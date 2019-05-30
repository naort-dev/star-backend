import datetime

def date_format_conversion(date):
    """
    The Function will convert the format of the expiry date in the register version 2 API into suitable format
    suitable format : YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ].
    :param date:
    :return:
    """
    if date:
        elements = date.split(" ")
        elements = elements[1:5]
        date = " ".join(elements)
        date = datetime.datetime.strptime(date, '%b %d %Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S.%f+05:30')
        return date
    else:
        return None

