"""V1 request/response validation. Local timers enforce deadlines outside the wire schema."""
from .scene import integer, validate as validate_scene

DISPLAY_STATES={"active","idle","recalculating","unavailable","arrived","stale_source","stale_transport"}


def header(value, kinds):
    if not isinstance(value,dict):return ['dictionary required']
    errors=[]
    if not integer(value.get('version'),1,1):errors.append('version')
    if not isinstance(value.get('kind'),str) or value['kind'] not in kinds:errors.append('kind')
    if not isinstance(value.get('epoch'),str) or not 1<=len(value['epoch'])<=64:errors.append('epoch')
    if not integer(value.get('requestId'),1,1_000_000):errors.append('requestId')
    return errors


def validate_request(value):
    errors=header(value,{'junction_request'})
    if not isinstance(value,dict):return errors
    fields=('displayedSession','displayedGeneration','displayedSeq','displayedState')
    if any(k in value for k in fields):
        if not isinstance(value.get('displayedSession'),str) or not 1<=len(value['displayedSession'])<=64:errors.append('displayedSession')
        for key in ('displayedGeneration','displayedSeq'):
            if not integer(value.get(key),0,1_000_000):errors.append(key)
        if not isinstance(value.get('displayedState'),str) or value['displayedState'] not in DISPLAY_STATES:errors.append('displayedState')
    return errors


def validate_reply(value):
    errors=header(value,{'junction_snapshot','junction_unavailable'})
    if not isinstance(value,dict):return errors
    if value.get('kind')=='junction_snapshot':errors+=validate_scene(value.get('scene'))
    elif value.get('kind')=='junction_unavailable':
        if 'scene' in value:errors.append('unavailable must not contain scene')
        if not isinstance(value.get('reason'),str) or len(value['reason'])>80:errors.append('reason')
    return errors
