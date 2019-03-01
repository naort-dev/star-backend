import csv, sys

def parse_file(filename):
    lines = dict()
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            lines[row['Name']] = row
    return lines, reader.fieldnames

def compare_lines(line1, line2, fieldnames, diff):
    result = True
    for field in fieldnames[2:]:
        value1 = float(line1[field])
        value2 = float(line2[field])
        if not(value2*(1. - diff) <= value1 <= value2*(1. + diff)):
            print('%s %s %s %f != %f' % (line1['Method'], line1['Name'], field, value1, value2))
            result = False
    return result

if __name__ == '__main__':
    lines1, fieldnames1 = parse_file(sys.argv[1])
    lines2, fieldnames2 = parse_file(sys.argv[2])
    diff = float(sys.argv[3])/100.
    result = True
    for key in lines1:
        if not compare_lines(lines1[key], lines2[key], fieldnames1, diff):
            result = False
    exit(0 if result else 1)
