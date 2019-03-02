import jinja2, csv, boto3, sys
from collections import OrderedDict
CHARSET = "UTF-8"

def to_lines(filename):
    lines = OrderedDict()
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lines[row['Name']] = row
    return lines, reader.fieldnames

threshold_percent = 30

def increase_ok(diff, percent):
    return ('green' if percent >= -threshold_percent else 'red', 'white' if percent >= -threshold_percent else 'red')

def decrease_ok(diff, percent):
    return ('green' if percent <= threshold_percent else 'red', 'white' if percent <= threshold_percent else 'red')

def expected_zero(diff, percent):
    return ('green' if diff == 0 else 'red', 'white' if diff == 0 else 'red')

def no_style(diff, percent):
    return ('', '')

field_styles = {
    '# requests': increase_ok,
    '# failures': expected_zero,
    'Median response time':    decrease_ok,
    'Average response time': decrease_ok,
    'Min response time': decrease_ok,
    'Max response time': decrease_ok,
    'Average Content Size': no_style,
    'Requests/s': increase_ok
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
        diffs_line[field] = (diff_format % (diff, percent_str) if percent_str and diff else '', field_styles[field](diff, percent), diff, percent)
        if not(expected_value*(1. - threshold_percent/100.) <= actual_value <= expected_value*(1. + threshold_percent/100.)):
            print('%s %s %s %f != %f' % (actual_line['Method'], actual_line['Name'], field, actual_value, expected_value))
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
    expected = 'expected_requests.csv'
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

    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)

    template = templateEnv.get_template('template.html.jinja2')
    outputText = template.render(lines=actual_lines, fieldnames=fieldnames1, diffs=diffs)
    with open("report_requests.html", "w") as output:
        output.write(outputText)
    send('build@starsona.com', topic_arn, 'Performance test %s' % ('SUCCESSFUL' if result else 'FAILED'), outputText)
    exit(0 if result else 1)

