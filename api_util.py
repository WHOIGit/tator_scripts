
from functools import lru_cache

import argparse
import tator
from tator.openapi.tator_openapi.models import Project, Media, LocalizationType, Version, User

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('TOKEN', help='A tator api token')
    parser.add_argument('--HOST', default='https://tator.whoi.edu', help='Tator Server URL, default is "https://tator.whoi.edu"')
    parser.add_argument('--user', '-u', help='Username or ID of a User. "list" will list all users')
    parser.add_argument('--project', '-p', help='Name or ID of the Project. Required for media, loctype, version string-name lookup. "list" will list all projects')
    parser.add_argument('--media', '-m', help='Name or ID of the Media. "list" will list all video media for given project')
    parser.add_argument('--loctype', '-l', help='Name or ID of the LocalizationType. "list" will list all localization types for given project')
    parser.add_argument('--version', '-v', help='Name or ID of the Version. "list" will list all versions for given project')
    
    args = parser.parse_args()
    
    if not args.project:
        if args.media and not args.media.isdigit():
            parser.error('--project NOT SET. Required for --media string-query')

        if args.loctype and not args.loctype.isdigit():
            parser.error('--project NOT SET. Required for --loctype string-query')
            
        if args.version and not args.version.isdigit():
            parser.error('--project NOT SET. Required for --version string-query')
            
    return args


@lru_cache(maxsize=None, typed=True)
def get_project(api, query):
    #if isinstance(query,Project):
    #    return query
    if str(query).isdigit(): 
        query = int(query)
    if isinstance(query, int):
        return api.get_project(query)
    else:
        project_objs = api.get_project_list()
        if query=='list':
            return project_objs
        project_objs = [p for p in project_objs if p.name == query]
        assert len(project_objs)==1, f'Duplicate Project Found for {"query"}: {[obj.id for obj in project_objs]}' if len(project_objs)>1 else f'Project Not Found: "{query}"'
        return project_objs[0]


def get_project_id(api, p):
    assert p != None, 'Must Specify a Project'
    if isinstance(p, Project):
        return p.id
    elif isinstance(p, str):
        if p.isdigit():
            return int(p)
        else:
            project = get_project(api, p)
            return project.id
    elif isinstance(p,int):
        return p

@lru_cache(maxsize=None, typed=True)
def get_media(api, query, project=None):
    #if isinstance(query, Media):
    #    return query
    if str(query).isdigit(): 
        query = int(query)
    if isinstance(query, int):
        return api.get_media(query)
    else:
        
        project_id = get_project_id(api, project)
        
        if query=='list':
            project_objs = api.get_media_list(project_id, dtype='video')
            return sorted(project_objs, key = lambda p: p.id)
        
        media_objs = api.get_media_list(project, name=query)

        assert len(media_objs)==1, f'Duplicate Media Found for "{query}": {[obj.id for obj in media_objs]}' if len(media_objs)>1 else f'Media Not Found: "{query}"{"" if "." in query else ". Did you remember to include a file extention like .mp4?" }'
        return media_objs[0]
        
        
@lru_cache(maxsize=None, typed=True)
def get_version(api, query, project=None, autocreate=False):
    #if isinstance(query,Version):
    #    return query
    if str(query).isdigit(): 
        query = int(query)
    if isinstance(query, int):
        return api.get_version(query)
    else:
        
        project_id = get_project_id(api, project)
            
        version_objs = api.get_version_list(project_id)
        if query=='list':
            return sorted(version_objs, key = lambda v: v.id)
        
        version_objs = [v for v in version_objs if v.name == query]

        if len(version_objs)==1:
            return version_objs[0]            
        elif len(version_objs)>1:
            raise AssertionError(f'Duplicate Versions Found for "{query}": {[obj.id for obj in version_objs]}')
        elif autocreate:
            print(f'Creating new Version: "{query}"')
            new_version_spec = dict(name=query)
            version_create_response = api.create_version(project_id, new_version_spec)
            print(version_create_response)  # TODO remove
            return api.get_version(version_create_response.id)
        else:
            raise KeyError(f'Version Not Found: "{query}"')
        
        
@lru_cache(maxsize=None, typed=True)
def get_loctype(api, query, project=None):
    #if isinstance(query, LocalizationType):
    #    return query
    if str(query).isdigit(): 
        query = int(query)
    if isinstance(query, int):
        return api.get_localization_type(query)
    else:

        project_id = get_project_id(api, project)

        loctype_objs = api.get_localization_type_list(project_id)
        if query=='list':
            return loctype_objs
        loctype_objs = [lt for lt in loctype_objs if lt.name == query]
        assert len(loctype_objs)==1, f'Duplicate Versions Found for "{query}": {[obj.id for obj in loctype_objs]}' if len(loctype_objs)>1 else f'LocalizationType Not Found: "{query}"'
        return loctype_objs[0]

@lru_cache(maxsize=None, typed=True)
def get_user(api, username_or_id):
    #if isinstance(username_or_id,User):
    #    return username_or_id
    if str(username_or_id).isdigit(): 
        query = int(username_or_id)
    if isinstance(username_or_id, int):
        return api.get_user(query)
    elif username_or_id=='list':
        users = api.get_user_list()
        return sorted(users, key = lambda u: u.id)
    else:
        return api.get_user_list(username=username_or_id)[0]



if __name__=='__main__':
    args = cli()
    api = tator.get_api(args.HOST, args.TOKEN)

    if args.user:
        user = get_user(api, args.user)
        if isinstance(user, list):
            print('USERS')
            for u in user:
                print(f'{u.id: 4d} "{u.username}"')
        else: 
            print(f'USER: "{user.username}" id={user.id}')
        
    if args.project:
        project = get_project(api, args.project)
        if isinstance(project, list):
            print('PROJECTS')
            for p in project:
                print(f'{p.id: 4d} "{p.name}"')
        else: 
            print(f'PROJECT: "{project.name}" id={project.id}')
            project_id = project.id
    else: project_id = None
        
    if args.media:
        media = get_media(api, args.media, project_id )
        if isinstance(media, list):
            print('MEDIA')
            for m in media:
                print(f'{m.id: 4d} "{m.name}"')
        else: 
            print(f'MEDIA: "{media.name}" id={media.id}')
       
    if args.loctype:
        loctype = get_loctype(api, args.loctype, project_id)
        if isinstance(loctype, list):
            print('LOCALIZATION TYPES')
            for l in loctype:
                print(f'{l.id: 4d} "{l.name}"')
        else: 
            print(f'LOCALIZATION TYPE: "{loctype.name}" id={loctype.id}')
        
    if args.version:
        version = get_version(api, args.version, project_id)
        if isinstance(version, list):
            print('VERSIONS')
            for v in version:
                print(f'  {v.id: 4d} "{v.name}"')
        else: 
            print(f'VERSION: "{version.name}" id={version.id}')
    





