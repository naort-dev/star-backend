import jinja2, csv, boto3, sys, os
from collections import OrderedDict
from pathlib import Path

CHARSET = "UTF-8"
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

def to_lines(filename):
    lines = OrderedDict()
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lines[row['Name']] = row
    return lines, reader.fieldnames

threshold_percent = 30

def increase_ok(diff, percent):
    return ('green' if percent >= 0 else ('orange' if percent >= -threshold_percent else 'red'), 'green' if percent >= threshold_percent else ('white' if percent >= -threshold_percent else 'red'))

def decrease_ok(diff, percent):
    return ('green' if percent <= 0 else ('orange' if percent <= threshold_percent else 'red'), 'green' if percent <= -threshold_percent else ('white' if percent <= threshold_percent else 'red'))

def expected_zero(diff, percent):
    return ('green' if diff == 0 else 'red', 'white' if diff == 0 else 'red')

def no_style(diff, percent):
    return ('', '')

field_styles = {
    '# requests': (increase_ok, True),
    '# failures': (expected_zero, True),
    'Median response time': (decrease_ok, True),
    'Average response time': (decrease_ok, True),
    'Min response time': (decrease_ok, False),
    'Max response time': (decrease_ok, False),
    'Average Content Size': (decrease_ok, False),
    'Requests/s': (increase_ok, True)
}

def diff_lines(actual_line, expected_line, fieldnames):
    diffs_line = dict()
    result = True
    for field in fieldnames[2:]:
        diff_format = '%+.2f%s' if '.' in actual_line[field] else '%+d%s'
        actual_value = float(actual_line[field])
        if field not in expected_line:
            continue
        expected_value = float(expected_line[field])
        diff = actual_value - expected_value
        percent = 0 if expected_value == 0 else int(100 * diff/expected_value)
        percent_str = '' if expected_value == 0 else '(%d%%)' % percent
        style, measure = field_styles[field]
        diffs_line[field] = (diff_format % (diff, percent_str) if percent_str and diff else '', style(diff, percent), diff, percent)
        if measure and not(expected_value*(1. - threshold_percent/100.) <= actual_value <= expected_value*(1. + threshold_percent/100.)):
            print('%s %s %s %.2f != %.2f' % (actual_line['Method'], actual_line['Name'], field, actual_value, expected_value))
            result = False

    return diffs_line, result

def list_sns_topic(topic):
    client = boto3.client('sns')
    subscriptions = client.list_subscriptions_by_topic(TopicArn=topic)
    return [subscription['Endpoint'] for subscription in subscriptions['Subscriptions'] if subscription['Protocol'] == 'email']

def send(sender, topic, subject, body):
    client = boto3.client('ses')

    client.send_email(
        Destination={
            'ToAddresses': list_sns_topic(topic),
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': CHARSET,
                    'Data': body,
                }
            },
            'Subject': {
                'Charset': CHARSET,
                'Data': subject,
            },
        },
        Source=sender,
    )


if __name__ == '__main__':
    topic_arn = sys.argv[1]
    expected = os.path.join(__location__, 'expected_requests.csv')
    actual = 'actual_requests.csv'
    actual_lines, fieldnames1 = to_lines(actual)
    expected_lines, fieldnames2 = to_lines(expected)
    diffs = dict()
    result = True
    for key in actual_lines:
        actual_line = actual_lines[key]
        expected_line = expected_lines[key]
        diffs[key], result_line = diff_lines(actual_line, expected_line, fieldnames1)
        if not result_line:
            result = False

    templateLoader = jinja2.FileSystemLoader(searchpath=__location__)
    templateEnv = jinja2.Environment(loader=templateLoader)
    revision_url = '%s/commits/%s' % (Path('.bitbucket/BITBUCKET_GIT_HTTP_ORIGIN').read_text().strip(), Path('.bitbucket/BITBUCKET_COMMIT').read_text().strip())
    commit_stat = Path('.bitbucket/BITBUCKET_COMMIT_STAT').read_text()

    template = templateEnv.get_template('template.html.jinja2')
    outputText = template.render(lines=actual_lines, fieldnames=fieldnames1, diffs=diffs, result=result, threshold=threshold_percent, revision_url=revision_url, commit_stat=commit_stat)
    with open("report_requests.html", "w") as output:
        output.write(outputText)
    send('build@starsona.com', topic_arn, 'Performance test %s' % ('SUCCESSFUL' if result else 'FAILED'), outputText)
    exit(0 if result else 1)

