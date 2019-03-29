from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import DocType, Text, Search, Integer, Q
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
from config.constants import *
from utilities.utils import get_bucket_url, get_elasticsearch_connection_params
from .constants import *
from faker import Faker


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


def bulk_indexing():
    connection_params = get_elasticsearch_connection_params()
    connections.create_connection(**connection_params)
    es = Elasticsearch(**connection_params)
    Professions.init(index=ES_PROFESSION_INDEX)
    Celebrities.init(index=ES_CELEBRITY_INDEX)
    # bulk(client=es, actions=(profession_indexing(profession) for profession in Profession.objects.all().iterator()))
    # bulk(client=es, actions=(
    #     celebrity_indexing(celebrity)
    #     for celebrity in Celebrity.objects.filter(admin_approval=True, availability=True).all().iterator()
    # ))
    bulk(client=es, actions=(prof_indexing(i) for i in range(10000)))
    bulk(client=es, actions=(celeb_indexing(i) for i in range(10000)))


def prof_indexing(i):
    fake = Faker()
    obj = Professions(
        meta={'id': i},
        id=i,
        title=fake.job(),
        parent_id=fake.random.randint(1, 10000)
    )
    obj.save(index=ES_PROFESSION_INDEX, op_type='index')

    return obj.to_dict(include_meta=True)


def celeb_indexing(i):
    fake = Faker()
    first_name = fake.first_name()
    last_name = fake.last_name()
    nick_name = first_name + ' ' + last_name
    obj = Celebrities(
        meta={'id': i},
        user_id=fake.random.randint(1, 10000),
        first_name=first_name,
        last_name=last_name,
        nick_name=nick_name,
        avatar_photo='',
        image_url='',
        thumbnail_url='',
        professions=fake.job()
    )
    obj.save(index=ES_CELEBRITY_INDEX, op_type='index')

    return obj.to_dict(include_meta=True)


def profession_indexing(profession):
    obj = Professions(
        meta={'id': profession.id},
        id=profession.id,
        title=profession.title,
        parent_id=profession.parent_id
    )
    obj.save(index=ES_PROFESSION_INDEX, op_type='index')

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
    obj.save(index=ES_CELEBRITY_INDEX, op_type='index')

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
