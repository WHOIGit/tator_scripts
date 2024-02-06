import os.path
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
    parser.add_argument('--mediatype', help='Name or ID of the MediaType. "list" will list all media types for given project')
    parser.add_argument('--loctype', '-l', help='Name or ID of the LocalizationType. "list" will list all localization types for given project')
    parser.add_argument('--version', '-v', help='Name or ID of the Version. "list" will list all versions for given project')
    parser.add_argument('--statetype', '-s', help='Name or ID of the StateType. "list" will list all StateTypes for given project')
    parser.add_argument('--leaftype', '-f', help='Name or ID of the LeafType. "list" will list all LeafTypes for given project')
    parser.add_argument('--leaf', default='list', help='Name or ID of a Leaf. "list" (default) will list all Leaf objects for given LeafType')
    
    args = parser.parse_args()

    if os.path.isfile(args.TOKEN):
        with open(args.TOKEN) as f:
            args.TOKEN = f.read().strip()
    
    if not args.project:
        if args.media and not args.media.isdigit():
            parser.error('--project NOT SET. Required for --media string-query')

        if args.loctype and not args.loctype.isdigit():
            parser.error('--project NOT SET. Required for --loctype string-query')
            
        if args.version and not args.version.isdigit():
            parser.error('--project NOT SET. Required for --version string-query')

        if args.statetype and not args.statetype.isdigit():
            parser.error('--project NOT SET. Required for --statetype string-query')

    return args


def add_arg_ids(api,args):
    if 'project' in args and args.project != 'list':
        args.project_id = get_project_id(api,args.project)
    if 'user' in args and args.user != 'list':
        args.user_id = get_user(api,args.user).id
    if 'media' in args and args.media != 'list':
        args.media_id = get_media(api,args.media,project=args.project_id)
    if 'mediatype' in args and args.mediatype != 'list':
        args.mediatype_id = get_mediatype(api,args.mediatype,project=args.project_id).id
    if 'loctype' in args and args.loctype != 'list':
        args.loctype_id = get_loctype(api,args.loctype,project=args.project_id).id
    if 'version' in args and args.version != 'list':
        args.version_id = get_version(api,args.version,project=args.project_id).id
    if 'statetype' in args and args.statetype != 'list':
        args.statetype_id = get_statetype(api, args.version, project=args.project_id).id
    if 'leaftype' in args and args.leaftype != 'list':
        args.leaftype_id = get_leaftype(api, args.leaftype, project=args.project_id).id
        if 'leaf' in args and args.leaf != 'list':
            args.leaf_id = get_leaf(api, args.leaf, args.leaftype, project=args.project_id).id


@lru_cache(maxsize=None, typed=True)
def get_project(api, query):
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
    assert p is not None, 'Must Specify a Project'
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
    project_id = get_project_id(api, project)

    if query=='list':
        project_objs = api.get_media_list(project_id, dtype='video')
        return sorted(project_objs, key = lambda p: p.id)

    media_objs = api.get_media_list(project, name=query)

    assert len(media_objs)==1, f'Duplicate Media Found for "{query}": {[obj.id for obj in media_objs]}' if len(media_objs)>1 else f'Media Not Found: "{query}"{"" if "." in query else ". Did you remember to include a file extention like .mp4?" }'
    return media_objs[0]

def get_media_id(api, m, project=None):
    assert m is not None, 'Media query is None'
    if isinstance(m, Media):
        return m.id
    elif isinstance(m, str):
        if m.isdigit():
            return int(m)
        else:
            m = get_media(api, m, project)
            return m.id
    elif isinstance(m,int):
        return m

@lru_cache(maxsize=None, typed=True)
def get_medias(api, queries:tuple, project=None):
    project_id = get_project_id(api, project)
    if all([isinstance(elem,int) for elem in queries]):
        return api.get_media_list_by_id(project_id, tator.models.MediaIdQuery(ids=queries))
    return [get_media(api,elem,project_id) for elem in queries]


@lru_cache(maxsize=None, typed=True)
def get_mediatype(api, query, project=None):
    if str(query).isdigit():
        query = int(query)
    if isinstance(query, int):
        return api.get_media_type(query)
    project_id = get_project_id(api, project)

    mediatype_objs = api.get_media_type_list(project_id)

    if query=='list':
        return sorted(mediatype_objs, key = lambda p: p.id)

    mediatype_obj = [mt for mt in mediatype_objs if mt.name==query]
    assert len(mediatype_obj)==1, f'Duplicate MediaType Found for "{query}": {[obj.id for obj in mediatype_obj]}' if len(mediatype_obj)>1 else f'Media Not Found: "{query}"'
    return mediatype_obj[0]


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
            new_version_spec = dict(name=query, show_empty=False)
            if isinstance(autocreate,str):
                new_version_spec['description'] = autocreate
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
def get_statetype(api, query, project=None):
    #if isinstance(query, StateType):
    #    return query
    if str(query).isdigit():
        query = int(query)
    if isinstance(query, int):
        return api.get_state_type(query)
    else:

        project_id = get_project_id(api, project)

        statetype_objs = api.get_state_type_list(project_id)
        if query=='list':
            return statetype_objs
        statetype_objs = [st for st in statetype_objs if st.name == query]
        assert len(statetype_objs)==1, f'Duplicate Versions Found for "{query}": {[obj.id for obj in statetype_objs]}' if len(statetype_objs)>1 else f'LocalizationType Not Found: "{query}"'
        return statetype_objs[0]


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


@lru_cache(maxsize=None, typed=True)
def get_leaftype(api, query, project=None):
    #if isinstance(query, LeafType):
    #    return query
    if str(query).isdigit():
        query = int(query)
    if isinstance(query, int):
        return api.get_leaf_type(query)
    else:

        project_id = get_project_id(api, project)

        leaftype_objs = api.get_leaf_type_list(project_id)
        if query=='list':
            return leaftype_objs
        leaftype_objs = [lt for lt in leaftype_objs if lt.name == query]
        assert len(leaftype_objs)==1, f'Duplicate Versions Found for "{query}": {[obj.id for obj in leaftype_objs]}' if len(leaftype_objs)>1 else f'LeafType Not Found: "{query}"'
        return leaftype_objs[0]

@lru_cache(maxsize=None, typed=True)
def get_leaf(api, query, leaftype, project, att='path'):
    #if isinstance(query, Leaf):
    #    return query
    if str(query).isdigit():
        query = int(query)
    if isinstance(query, int):
        return api.get_leaf(query)
    else:

        project_id = get_project_id(api, project)
        leaftype_id = get_leaftype(api, leaftype).id

        leaf_objs = api.get_leaf_list(project_id, type=leaftype_id)
        if query=='list':
            leaf_objs.sort(key=lambda leaf: getattr(leaf,att))
            return leaf_objs
        
        if att in ['name','id']: 
            leaf_objs = [leaf for leaf in leaf_objs if query == getattr(leaf,att)]
            assert len(leaf_objs)==1, f'Duplicate Versions Found for "{query}": {[obj.id for obj in leaf_objs]}' if len(leaf_objs)>1 else f'Leaf Not Found: "{query}"'
            return leaf_objs[0]
        else:
            leaf_objs = [leaf for leaf in leaf_objs if query in getattr(leaf,att)]
            return leaf_objs

def get_leaves(api, project, leaftype=None):
    if leaftype is None:
        leaftypes = get_leaftype(api, 'list', project)
        assert len(leaftypes)==1, f'Multiple LeafTypes in project "{project}", please specify LeafType'
    return get_leaf(api, 'list', leaftypes[0].id, project)


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
            #print(loctype)
        
    if args.version:
        version = get_version(api, args.version, project_id)
        if isinstance(version, list):
            print('VERSIONS')
            for v in version:
                print(f'  {v.id: 4d} "{v.name}"')
        else: 
            print(f'VERSION: "{version.name}" id={version.id}')
    
    if args.statetype:
        statetype = get_statetype(api,args.statetype, project_id)
        if isinstance(statetype, list):
            print('STATE TYPES')
            for s in statetype:
                print(f'{l.id: 4d} "{s.name}"')
        else:
            print(f'STATE TYPE: "{statetype.name}" id={statetype.id}')

    if args.leaftype:
        leaftype = get_leaftype(api, args.leaftype, project_id)
        def leafprint(leaves):
            if not leaves: return
            if isinstance(leaves,list):
                print('  LEAVES')
                for leaf in leaves:
                    print(f'{leaf.id: 6d}  {leaf.path}')
            else:
                print(f'LEAF: "{leaves.path}" id={leaves.id}')
                #print(leaves)
        if isinstance(leaftype, list):
            print('LEAF TYPES')
            for l in leaftype:
                leafcount_str=''
                if args.leaf == 'list':
                    leaves = get_leaf(api, args.leaf, l.id, project_id)
                    leafcount_str = f'({len(leaves)} leaves)'
                print(f'{l.id: 4d} "{l.name}" {leafcount_str}')
        else:
            print(f'LEAF TYPE: "{leaftype.name}" id={leaftype.id}')
            if args.leaf:
                leaves = get_leaf(api, args.leaf, leaftype.id, project_id)
                leafprint(leaves)
                
            

