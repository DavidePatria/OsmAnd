"""Reference for JC1 lossless SDK byte-array transport; logical contracts unchanged."""
WORDS=['active','idle','recalculating','unavailable','map_context','layer_context','routing_branches','route_only','selected','branch','context','motorcycle road context; intersections do not imply connectivity','motorcycle road context with level ordering']+[f'j{i}' for i in range(4)]+[f'c{i}' for i in range(1,41)]+['arrived']


def encode(reply,version=2):
    if version not in (1,2):raise ValueError('version')
    if version==1 and (reply.get('scene',{}).get('state')=='arrived' or 'destination' in reply.get('scene',{})):raise ValueError('version 1 extension')
    data=bytearray()
    def u(n):
        if type(n) is not int or not 0<=n<=2_000_000:raise ValueError('integer')
        while n>=128:data.append((n&127)|128);n>>=7
        data.append(n)
    def s(n):u(-2*n-1 if n<0 else 2*n)
    def text(v):
        pool=WORDS[:-1] if version==1 else WORDS
        token=pool.index(v)+1 if v in pool else 0;u(token)
        if not token:
            raw=v.encode('utf-8')
            if len(raw)>320:raise ValueError('string')
            u(len(raw));data.extend(raw)
    for n in (74,67,version,int(reply['kind']=='junction_unavailable')):u(n)
    text(reply['epoch']);u(reply['requestId'])
    if reply['kind']=='junction_unavailable':text(reply['reason'])
    else:
        v=reply['scene'];text(v['session']);u(v['generation']);u(v['seq'])
        for k in ('state','geometryMode','reason','roadName','maneuver'):text(v[k])
        for k in ('distanceM','sourceAgeMs','fixAgeMs','radiusDm'):u(v[k])
        u(int('progressAgeMs' in v))
        if 'progressAgeMs' in v:u(v['progressAgeMs']);u(v['speedDmps'])
        u(len(v['anchors']))
        for a in v['anchors']:
            text(a['id']);u(a['routeIndex']);s(a['point'][0]);s(a['point'][1])
        u(len(v['paths']))
        for p in v['paths']:
            text(p['id']);text(p['role']);u(len(p['points']));x=y=0
            for nx,ny in p['points']:s(nx-x);s(ny-y);x,y=nx,ny
            u(len(p['anchorRefs']))
            for ref,idx in p['anchorRefs']:u(next(i for i,a in enumerate(v['anchors']) if a['id']==ref));u(idx)
            if v['geometryMode']=='layer_context':
                s(p['layer'])
                if p['role']=='selected':
                    for n in p['segmentLayers']:s(n)
        if version==2:
            u(int('destination' in v))
            if 'destination' in v:s(v['destination'][0]);s(v['destination'][1])
    if len(data)>8192:raise ValueError('byte bound')
    return bytes(data)


def decode(data):
    if len(data)>8192:raise ValueError('byte bound')
    at=0
    def u():
        nonlocal at
        n=0
        for i in range(3):
            if at>=len(data):raise ValueError('truncated')
            b=data[at];at+=1;n|=(b&127)<<(i*7)
            if b<128:
                if n>2_000_000 or (i and b==0):raise ValueError('integer')
                return n
        raise ValueError('integer')
    def s():
        n=u();return -(n+1)//2 if n&1 else n//2
    def count(limit):
        n=u()
        if n>limit:raise ValueError('count')
        return n
    def text():
        nonlocal at
        token=count(len(WORDS)-(version==1))
        if token:return WORDS[token-1]
        n=count(320)
        if at+n>len(data):raise ValueError('truncated')
        result=data[at:at+n].decode('utf-8');at+=n;return result
    if [u(),u()]!=[74,67]:raise ValueError('magic')
    version=u()
    if version not in (1,2):raise ValueError('version')
    kind=count(1);reply={'version':1,'kind':'junction_unavailable' if kind else 'junction_snapshot','epoch':text(),'requestId':u()}
    if kind:reply['reason']=text()
    else:
        v={'version':1,'session':text(),'generation':u(),'seq':u()}
        for k in ('state','geometryMode','reason','roadName','maneuver'):v[k]=text()
        for k in ('distanceM','sourceAgeMs','fixAgeMs','radiusDm'):v[k]=u()
        if count(1):v['progressAgeMs']=u();v['speedDmps']=u()
        anchors=[]
        for _ in range(count(4)):anchors.append({'id':text(),'routeIndex':u(),'point':[s(),s()]})
        paths=[];total=0
        for _ in range(count(40)):
            p={'id':text(),'role':text()};size=count(48);total+=size
            if size<2 or total>512:raise ValueError('points')
            x=y=0;points=[]
            for _ in range(size):x+=s();y+=s();points.append([x,y])
            refs=[]
            for _ in range(count(4)):
                a=u();idx=u()
                if a>=len(anchors):raise ValueError('anchor')
                refs.append([anchors[a]['id'],idx])
            p.update(points=points,anchorRefs=refs)
            if v['geometryMode']=='layer_context':
                p['layer']=s()
                if p['role']=='selected':p['segmentLayers']=[s() for _ in range(size-1)]
            paths.append(p)
        v.update(anchors=anchors,paths=paths);reply['scene']=v
        if version==2 and count(1):v['destination']=[s(),s()]
    if at!=len(data):raise ValueError('trailing')
    return reply
