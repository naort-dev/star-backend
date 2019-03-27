from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import DocType, Text, Search, Integer, Q
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from urllib.parse import urlparse
from users.models import Profession, Celebrity
from config.constants import *
from utilities.utils import get_bucket_url
from .constants import *
import os
import boto3


class Professions(DocType):
    title = Text()
    parent_id = Integer()


class Celebrities(DocType):
    user_id = Integer()
    first_name = Text()
    last_name = Text()
    nick_name = Text()
    professions = Text()
    avatar_photo = Text()
    image_url = Text()
    thumbnail_url = Text()

def get_elasticsearch_connection_params():
    endpoint = urlparse(os.environ.get('ELASTICSEARCH_ENDPOINT'))
    service = endpoint.hostname.split('.')[-3]
    region = endpoint.hostname.split('.')[-4]
    use_ssl = endpoint.scheme == 'https'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    
    return dict(
        hosts=[{'host': endpoint.hostname, 'port': endpoint.port}],
        http_auth=awsauth,
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        connection_class = RequestsHttpConnection,
        timeout=300)

def bulk_indexing():
    connection_params = get_elasticsearch_connection_params()
    connections.create_connection(**connection_params)
    es = Elasticsearch(**connection_params)
    Professions.init(index=ES_PROFESSION_INDEX)
    bulk(client=es, actions=(profession_indexing(profession) for profession in Profession.objects.all().iterator()))
    Celebrities.init(index=ES_CELEBRITY_INDEX)
    bulk(client=es, actions=(
        celebrity_indexing(celebrity)
        for celebrity in Celebrity.objects.filter(admin_approval=True, availability=True).all().iterator()
    ))


def profession_indexing(profession):
    obj = Professions(
        meta={'id': profession.id},
        id=profession.id,
        title=profession.title,
        parent_id=profession.parent_id
    )
    obj.save(index='professions', op_type='index')

    return obj.to_dict(include_meta=True)


def celebrity_indexing(celebrity):
    obj = Celebrities(
        meta={'id': celebrity.id},
        user_id=celebrity.user_id,
        first_name=celebrity.user.first_name,
        last_name=celebrity.user.last_name,
        nick_name=celebrity.user.get_short_name(),
        avatar_photo=celebrity.user.avatar_photo.photo if celebrity.user.avatar_photo else '',
        image_url=get_s3_image_url(celebrity.user.avatar_photo) if celebrity.user.avatar_photo else '',
        thumbnail_url=get_s3_thumbnail_url(celebrity.user.avatar_photo) if celebrity.user.avatar_photo else '',
        professions=','.join([cp.profession.title for cp in celebrity.user.celebrity_profession.all()])
    )
    obj.save(index='celebrities', op_type='index')

    return obj.to_dict(include_meta=True)


def get_s3_image_url(obj):
    config = PROFILE_IMAGES
    return '{}/{}'.format(get_bucket_url(), config+obj.photo)


def get_s3_thumbnail_url(obj):
    if obj.thumbnail is not None:
        config = PROFILE_IMAGES
        return '{}/{}'.format(get_bucket_url(), config+obj.thumbnail)
    else:
        return ''
