import datetime
from job.tasks import check_file_exist_in_s3
import boto3
import os

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


def remove_files_from_s3(file):
    try:
        if check_file_exist_in_s3(file):
            objects = {'Objects': [{'Key': file}]}
            s3 = boto3.client('s3', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                              aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
            s3.delete_objects(Bucket=os.environ.get('AWS_STORAGE_BUCKET_NAME'), Delete=objects)
            print('The file : %s is successfully deleted from s3' % file)
    except Exception as e:
        print(str(e))
