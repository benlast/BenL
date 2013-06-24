#!/usr/bin/env python
# reaper.py
# AWS EC2 instance control
# (c) 2013 Ben Last <ben@benlast.com>

#Standard modules
import os, sys, argparse, types, re

#We use distutils.version to check versions of libraries
import distutils.version

#Import boto and check the version
BOTOVERSION='2.3.0'
import boto
if distutils.version.LooseVersion(boto.__version__) < distutils.version.LooseVersion(BOTOVERSION):
    raise RuntimeError("The minimum required version of the boto module is %s" % BOTOVERSION)

import boto.utils
import boto.ec2

#Check for test mode - if we are in test mode, we stub out certain functions and run self-tests
TESTMODE=("--test" in sys.argv)
if TESTMODE:
    print "Running in test mode"

#A keyword=value splitter that takes a string and returns a 2-tuple or raises
#an exception if there's a format error.
def splitKV(arg):
    """Split keyword from value at the first '=', strip both parts,return a 2-tuple.
    Lowercase the keyword, leave the value case alone."""

    eqpos=arg.find('=')
    if eqpos<0:
        #No =, so we have only a keyword, which is legal.
        return (arg.lower().strip(),None)

    (k,v)=(arg[:eqpos].lower().strip(),arg[eqpos+1:].strip())

    return (k,v)

class FilterAction(argparse.Action):
    """An argument parsing action for argparse that will store an include or exclude filter
    as a (keyword,value,isRegex) tuple, appending it to the appropriate attribute."""

    #Class constants - these are referenced in __call__ and where the arguments
    #are added to the parser.
    INCLUDETAGS=["-i","--include"]
    EXCLUDETAGS=["-x","--exclude"]
    INCLUDERTAGS=["-I","--includer"]
    EXCLUDERTAGS=["-X","--excluder"]
    RETAGS=INCLUDERTAGS+EXCLUDERTAGS    #All regexp option names
    ITAGS=INCLUDETAGS+INCLUDERTAGS      #All simple option names

    def __call__(self,parser,namespace,values,optionstring):
        """We expect that values is a (keyword,value) tuple because splitKV has already been
        applied to it."""
        if type(values)==types.TupleType and len(values)==2:
            #Determine if this is a regex option
            isRegex=(optionstring in FilterAction.RETAGS)
            #Determine if this is an include or exclude
            attr="includes" if (optionstring in FilterAction.ITAGS) else "excludes"
            #Split the value to get the keyword and value
            (k,v)=values
            #Append to the appropriate existing list of (k,v,isRegex) tuples
            setattr(namespace,attr,getattr(namespace,attr,[])+[(k,v,isRegex)])

def arguments(args=sys.argv[1:]):
    """Parse command line arguments and return the result of parsing."""
    parser=argparse.ArgumentParser(usage="""\
This program will identify all EC2 instances in the specified region (or the same region as this
instance, if running in EC2).  Filters may be used to include only some instances, or to
exclude some instances.  Filters operate by looking at the values of certain instance
attributes: specifically, those returned by the Python boto library for EC2 instances.

An include or exclude filter is specified as name=value.  There are two forms: simple and regular
expression.  A simple filter is specified with -i, --include, -x, --exclude and an instance is matched
if the named attribute matches the given value exactly.

A regular expression filter is specified with -I, --includer, -X, --excluder and an instanced is matched
if the named attribute matches the regular expression specified as the value.

There is a special rule for matching tags: specify them using the name tags.<tagname> (for example,
tags.name).  Tag names are treated as case-independent.

The rules for matching are:
1. Include filtering comes before exclude filtering.
2. If there are no include filters, all instances are considered to be selected, then exclusions are applied.
3. If there are no exclude filters, all included instances are selected.
If you specify --start, --stop or --terminate, then this action is applied to all the selected
instances.
If you don't specify any of --start, --stop or --terminate, then the instances are listed but
no action is taken.
""")

    parser.add_argument(*FilterAction.INCLUDETAGS,
        action=FilterAction,type=splitKV,dest='includes',default=[],
        help="Specify a simple inclusion filter (a keyword=value option where the value must match, including case)")

    parser.add_argument(*FilterAction.EXCLUDETAGS,action=FilterAction,type=splitKV,dest='excludes',default=[],
        help="Specify a simple exclusion filter (a keyword=value option where the value must match, including case)")

    parser.add_argument(*FilterAction.INCLUDERTAGS,action=FilterAction,type=splitKV,dest='includes',default=[],
        help="Specify a regex inclusion filter (a keyword=value option where the value is a regular expression)")

    parser.add_argument(*FilterAction.EXCLUDERTAGS,action=FilterAction,type=splitKV,dest='excludes',default=[],
        help="Specify a regex exclusion filter (a keyword=value option where the value is a regular expression)")

    parser.add_argument('-r','--region',action='store',dest='region',
        help="Specify the region to be scanned")

    parser.add_argument('--start',action='store_const',const='start',dest='action')
    parser.add_argument('--stop',action='store_const',const='stop',dest='action')
    parser.add_argument('--terminate',action='store_const',const='terminate',dest='action')

    parser.add_argument('-v','--verbose',action='count',dest='verbose',default=0,
        help="Increase verbosity of output")

    return parser.parse_args(args)

class Instance:
    """This class represents the information for an instance, in a form that is easily filterable.  We
    use a class of our own to wrap actual instance objects so that we can mock up test data easily, built
    from string representations of actual instance data."""
    def __init__(self,data):
        """Initialize either from a boto.ec2.instance.Instance or a dict: the latter may be used in
        test mode to create fake Instances."""
        if type(data) in [types.DictType,types.DictionaryType]:
            #Fake up from a string - eval the string to get a dict and then set the attributes of this object
            #from the dict.
            for (k,v) in data.iteritems():
                setattr(self,k,v)
        else:
            #We'll assume it's a boto.ec2.instance.Instance, and set attributes on self for every
            #non-builtin attribute in the object.
            map(lambda (k,v): setattr(self,k,v),((k,v) for (k,v) in data.__dict__.iteritems() if not k.startswith('__')))
            #Copy the bound control methods from the original object, replacing the test methods
            self.start=data.start
            self.stop=data.stop
            self.terminate=data.terminate

        if not hasattr(self,"tags"):
            self.tags={}
        else:
            #Rewrite the dict to have lower-case keys
            self.tags=dict([(a.lower(),b) for (a,b) in self.tags.iteritems()])

        # Store the underlying object
        self.instance=data

    def __unicode__(self):
        return u"id:%s name:'%s' State:%s"% (getattr(self,"id",u"(no id)"),
            self.tags.get("name",u"(no name)"),
            getattr(self,"state",u"(no state)"))

    def __str__(self):
        return unicode(self).encode('utf-8')

    def start(self):
        """Test mode implementation - sets state value"""
        self.state="started"

    def stop(self):
        """Test mode implementation - sets state value"""
        self.state="stopped"

    def terminate(self):
        """Test mode implementation - sets state value"""
        self.state="terminated"

def getAllInstances(region=None):
    """A generator that will yield an Instance for every instance found."""
    if TESTMODE:
        #Fake up a set of Instances
        testData="""[\
{'kernel': u'aki-31990e0b', 'root_device_type': u'ebs', 'private_dns_name': u'ip-172-31-22-97.ap-southeast-2.compute.internal',
'instanceState': u'\\n                    ', 'previous_state': None, 'public_dns_name': '', 'id': u'i-e48f12d9', 'deviceIndex': u'0',
'state_reason': {u'message': u'Client.UserInitiatedShutdown: User initiated shutdown', u'code': u'Client.UserInitiatedShutdown'},
'monitored': False, 'item': u'\\n                        ', 'subnet_id': u'subnet-08eb5161',
'block_device_mapping': {u'/dev/sda1': 'dummy'},
'shutdown_state': None, 'group_name': None, 'platform': None, 'state': u'running', 'deleteOnTermination': u'true',
'eventsSet': None, 'attachment': u'\\n                            ', 'attachmentId': u'eni-attach-eec41687',
'client_token': u'NvExu1371720135749', '_in_monitoring_element': False, 'virtualization_type': u'paravirtual',
'architecture': u'x86_64', 'ramdisk': None, 'description': '', 'tags': {u'Name': u'Sample1', u'Tag2': u'victoria', u'Tag1': u'Hello Dolly'},
'key_name': u'BenGeneralKeypair', 'interfaces': [], 'image_id': u'ami-04ea7a3e',
'reason': u'User initiated (2013-06-20 09:41:05 GMT)', 'tenancy': u'default',
'groups': ['dummy'],
'ownerId': u'132960571990', 'spot_instance_request_id': None,
'monitoring': u'\\n                    ', 'requester_id': None, 'state_code': 80,
'ip_address': None, 'sourceDestCheck': u'true', 'placement': u'ap-southeast-2b',
'attachTime': u'2013-06-20T09:22:17.000Z', 'ami_launch_index': u'0',
'dns_name': '', 'region': 'dummy', 'launch_time': u'2013-06-20T09:22:17.000Z',
'persistent': False, 'instance_type': u't1.micro',
'status': u'attached', 'root_device_name': u'/dev/sda1', 'hypervisor': u'xen',
'private_ip_address': u'172.31.22.97', 'vpc_id': u'vpc-09eb5160', 'product_codes': [], 'networkInterfaceId': u'eni-754e0a1c'},

{'kernel': u'aki-31990e0b', 'root_device_type': u'ebs', 'private_dns_name': u'ip-172-31-22-98.ap-southeast-2.compute.internal',
'instanceState': u'\\n                    ', 'previous_state': None, 'public_dns_name': '', 'id': u'i-e48f12da', 'deviceIndex': u'0',
'state_reason': {u'message': u'Client.UserInitiatedShutdown: User initiated shutdown', u'code': u'Client.UserInitiatedShutdown'},
'monitored': False, 'item': u'\\n                        ', 'subnet_id': u'subnet-08eb5161',
'block_device_mapping': {u'/dev/sda1': 'dummy'},
'shutdown_state': None, 'group_name': None, 'platform': None, 'state': u'stopped', 'deleteOnTermination': u'true',
'eventsSet': None, 'attachment': u'\\n                            ', 'attachmentId': u'eni-attach-eec41687',
'client_token': u'NvExu1371720135749', '_in_monitoring_element': False, 'virtualization_type': u'paravirtual',
'architecture': u'x86_64', 'ramdisk': None, 'description': '', 'tags': {u'Name': u'Sample2', u'Tag2': u'victoria', u'Tag1': u'Hello Dolly'},
'key_name': u'BenGeneralKeypair', 'interfaces': [], 'image_id': u'ami-04ea7a3e',
'reason': u'User initiated (2013-06-20 09:41:05 GMT)', 'tenancy': u'default',
'groups': ['dummy'],
'ownerId': u'132960571990', 'spot_instance_request_id': None,
'monitoring': u'\\n                    ', 'requester_id': None, 'state_code': 80,
'ip_address': None, 'sourceDestCheck': u'true', 'placement': u'ap-southeast-2b',
'attachTime': u'2013-06-20T09:22:17.000Z', 'ami_launch_index': u'0',
'dns_name': '', 'region': 'dummy', 'launch_time': u'2013-06-20T09:22:17.000Z',
'persistent': False, 'instance_type': u't1.micro',
'status': u'attached', 'root_device_name': u'/dev/sda1', 'hypervisor': u'xen',
'private_ip_address': u'172.31.22.98', 'vpc_id': u'vpc-09eb5160', 'product_codes': [], 'networkInterfaceId': u'eni-754e0a1c'},

{'kernel': u'aki-31990e0b', 'root_device_type': u'ebs', 'private_dns_name': u'ip-172-31-22-99.ap-southeast-2.compute.internal',
'instanceState': u'\\n                    ', 'previous_state': None, 'public_dns_name': '', 'id': u'i-e48f12db', 'deviceIndex': u'0',
'state_reason': {u'message': u'Client.UserInitiatedShutdown: User initiated shutdown', u'code': u'Client.UserInitiatedShutdown'},
'monitored': False, 'item': u'\\n                        ', 'subnet_id': u'subnet-08eb5162',
'block_device_mapping': {u'/dev/sda1': 'dummy'},
'shutdown_state': None, 'group_name': None, 'platform': None, 'state': u'terminated', 'deleteOnTermination': u'true',
'eventsSet': None, 'attachment': u'\\n                            ', 'attachmentId': u'eni-attach-eec41687',
'client_token': u'NvExu1371720135749', '_in_monitoring_element': False, 'virtualization_type': u'paravirtual',
'architecture': u'x86_64', 'ramdisk': None, 'description': '', 'tags': {u'Name': u'Sample3', u'Tag2': u'victoria', u'Tag1': u'Hello Dolly'},
'key_name': u'BenGeneralKeypair', 'interfaces': [], 'image_id': u'ami-04ea7a3e',
'reason': u'User initiated (2013-06-20 09:41:05 GMT)', 'tenancy': u'default',
'groups': ['dummy'],
'ownerId': u'132960571990', 'spot_instance_request_id': None,
'monitoring': u'\\n                    ', 'requester_id': None, 'state_code': 80,
'ip_address': None, 'sourceDestCheck': u'true', 'placement': u'ap-southeast-2b',
'attachTime': u'2013-06-20T09:22:17.000Z', 'ami_launch_index': u'0',
'dns_name': '', 'region': 'dummy', 'launch_time': u'2013-06-20T09:22:17.000Z',
'persistent': False, 'instance_type': u't1.micro',
'status': u'attached', 'root_device_name': u'/dev/sda1', 'hypervisor': u'xen',
'private_ip_address': u'172.31.22.99', 'vpc_id': u'vpc-09eb5160', 'product_codes': [], 'networkInterfaceId': u'eni-754e0a1c'}
]"""
        #testData evals to a list of dicts, and we will yield an Instance for each dict
        for data in eval(testData):
            yield Instance(data)
    else:
        #Not in test mode - yield actual instance data
        #The get_all_instances actually returns a list of reservations, each of which contains a list of instances.  So
        #we reduce() this via a generator to a list of instances, then yield each one.
        for instance in reduce(lambda x,y: x+y,(r.instances for r in boto.ec2.connect_to_region('ap-southeast-2').get_all_instances()),[]):
            yield Instance(instance)

class Filter:
    """Represents a single include/exclude filter.
    Create a filter by passing a (keyword,value,isRegex) tuple.
    Use call syntax to check if a give instance matches the Filter."""
    def __init__(self,kv):
        #Store the original value in _value so that we can print it for debug (because
        #in the case of a regex, self.value is the compiled regex object).
        (self.keyword,self._value,self.isRegex)=kv

        # Handle the special case of a tag filter: we look up on the key that
        # follows the '.'
        if self.keyword.startswith("tags.") or self.keyword.startswith("tag."):
            self.tag=self.keyword[self.keyword.find('.')+1:]
        else:
            # Setting self.tag to None flags that this is not a tag filter
            self.tag=None

        if self.isRegex:
            self.value=re.compile(self._value)
        else:
            self.value=self._value

    def __unicode__(self):
        return u"(%s,%s,%s)"%(self.keyword,self._value,self.isRegex)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __call__(self,instance):
        """Return True if this Filter matches the given instance (which
        is treated as an object that may have attributes matching the
        keyword for this Filter)."""
        if self.tag is None:
            attr=getattr(instance,self.keyword,None)
        else:
            #Get the tags value with the given tag name
            attr=getattr(instance,"tags",{}).get(self.tag)
        if attr is not None:
            if self.value is None:
                #All we're checking for is the presence of the attribute with *some* value
                #that is true (pythonically speaking, meaning 'not empty' in most cases).
                return bool(attr.strip())
            else:
                #Compare the values
                if self.isRegex:
                    # We don't care about the actual match value, just whether there is
                    # any match or not.
                    return (self.value.match(attr) is not None)
                else:
                    # We match on an exact string match
                    return (self.value==attr)
        #If there is no attribute with the given name, then we never match.
        return False

def createFilterList(data):
    """Given a list of (keyword,value,isRegex) tuples, return a list
    of Filters."""
    return [Filter(x) for x in data if type(x) in (types.TupleType,types.ListType) and len(x)==3]

def filtered(instances,includes,excludes):
    """Given a list of instances and filters for include/exclude, return the
    list of instances that pass the filters.
    The rules for matching are:
    1. Include filtering comes before exclude filtering.
    2. If there are no include filters, all instances are considered to be included.
    3. If there are no exclude filters, all included instances are returned.
    """
    if includes:
        # Check each instance against all filters (stopping at the first one that matches)
        included=filter(lambda i: any(f(i) for f in includes), instances)
    else:
        included=instances
    #print "Included=%s"%map(str,included)

    if excludes:
        # Check each instance against all filters (stopping at the first one that matches)
        passed=filter(lambda i: not any(f(i) for f in excludes), included)
    else:
        passed=included

    return passed

def test():
    """Run self-tests"""
    assert splitKV("a=b")==('a','b')
    assert splitKV("this is a keyword = this is a value")==('this is a keyword','this is a value')
    assert splitKV("Alpha=b")==("alpha","b")
    assert splitKV("Alpha=")==("alpha","")
    result=splitKV("Alpha")
    assert result==("alpha",None),"Expected ('alpha',None), got %s"%str(result)

    a=vars(arguments([]))
    assert not a['action'],"Expected empty action"
    assert not a['includes'],"Expected empty includes"
    assert not a['excludes'],"Expected empty excludes"
    assert not a['verbose'],"Expected empty verbose"

    assert arguments(["--start"]).action=='start',"Expected action to be start"
    assert arguments(["--stop"]).action=='stop',"Expected action to be stop"
    assert arguments(["--terminate"]).action=='terminate',"Expected action to be terminate"
    assert arguments("--stop --start".split()).action=='start',"Expected last action to take precedence"

    args = arguments("-i alpha=beta".split())
    assert args.includes==[("alpha","beta",False)],"Expected -i to specify an include, got includes=%s"%args.includes

    args=arguments("-i alpha=beta --includer eric=pig".split())
    a=args.includes

    assert len(a)==2,"Expected two includes"
    assert a[0]==("alpha","beta",False),"Expected first include to be alpha=beta"
    assert a[1]==("eric","pig",True),"Expected second include to be eric=pig"

    includeFilters = createFilterList(a)
    assert len(includeFilters)==2,"Expected two include filters"

    args=arguments(["-X=Batman=robin","--exclude","Joker=Heath Ledger","-x","eric=sow"])
    a=args.excludes
    assert len(a)==3,"Expected 3 excludes, got %s"%a
    assert a[0]==("batman","robin",True),"Expected first exclude to be batman=robin"
    assert a[1]==("joker","Heath Ledger",False),"Expected second include to be joker=heath ledger"

    excludeFilters = createFilterList(a)
    assert len(excludeFilters)==3,"Expected three exclude filters"

    # Basic filtering tests
    o1=Instance({"id":"o1","alpha":"beta","eric":"sow"})
    o2=Instance({"id":"o2","alpha":"gamma","eric":"pig"})
    o3=Instance({"id":"o3","alpha":"delta","eric":"swine"})
    il1=[o1,o2,o3]

    l1=filtered(il1,[],[])
    assert len(l1)==3,"Expected 3 instances, got %s"%l1
    assert l1==[o1,o2,o3],"Expected all instances, got %s"%l1

    l2=filtered(il1,includeFilters,[])
    assert len(l2)==2,"Expected 2 instances, got %s"%l2
    assert l2==[o1,o2],"Expected first two instances, got %s"%l1

    l3=filtered(il1,includeFilters,excludeFilters)
    assert len(l3)==1,"Expected 1 instance, got %s"%l3
    assert l3==[o2],"Expected second instance, got %s"%map(str,l3)

    instances=list(getAllInstances())   #convert generator to list
    assert len(instances)==3,"Expected three instances"
    assert instances[0].id==u'i-e48f12d9',"Expected instance 0 id to be u'i-e48f12d9'"
    assert instances[1].tags["name"]=="Sample2","Expected instance 1 to have name Sample2"
    assert instances[2].state=="terminated","Expected instance 3 to have state 'terminated'"

    args=arguments("-i id=i-e48f12d9".split())
    results=filtered(instances,createFilterList(args.includes),createFilterList(args.excludes))
    assert len(results)==1,"Expected one result, got %s"%map(str,results)

    args=arguments("-I id=i-e48f12d[9a]".split())
    results=filtered(instances,createFilterList(args.includes),createFilterList(args.excludes))
    assert len(results)==2,"Expected two results, got %s"%map(str,results)
    assert results[0].id=="i-e48f12d9"
    assert results[1].id=="i-e48f12da"

    args=arguments("-I id=i-e48f12d. -X id=i-e48f12db".split())
    iFilters=createFilterList(args.includes)
    assert len(iFilters)==1,"Expected one include filter, got %s"%iFilters

    xFilters=createFilterList(args.excludes)
    assert len(xFilters)==1,"Expected one exclude filter, got %s"%xFilters

    results=filtered(instances,iFilters,xFilters)
    assert len(results)==2,"Expected two results, got %s"%map(str,results)
    assert results[0].id=="i-e48f12d9"
    assert results[1].id=="i-e48f12da"

    args=arguments("-I id=i-e48f12d[ab] -X tags.name=Sample2".split())
    iFilters=createFilterList(args.includes)
    xFilters=createFilterList(args.excludes)
    results=filtered(instances,iFilters,xFilters)
    assert len(results)==1,"Expected one result, got %s"%map(str,results)
    assert results[0].id=="i-e48f12db"

    return True

def work(args={}):
    """Select instances according to any given filters, then apply any given actions (or just
    print some instance details if there are no actions)."""
    region=getattr(args,"region")
    if region:
        action=getattr(args,"action")
        #Filter all the instances in the region
        instances=filtered(getAllInstances(region==region),
            createFilterList(args.includes),
            createFilterList(args.excludes))
        for i in instances:
            if not action:
                print i
            else:
                #Get the current state and apply the action if appropriate
                state=getattr(i,"state",None)
                if action=="start":
                    if state not in ("running","pending","terminated"):
                        if args.verbose:
                            print "Starting %s"%i
                        i.start()
                    else:
                        if args.verbose:
                            print "Not starting %s"%i
                elif action=="stop":
                    if state in ("pending","running"):
                        if args.verbose:
                            print "Stopping %s"%i
                        i.stop()
                    else:
                        if args.verbose:
                            print "Not stopping %s"%i
                elif action=="terminate":
                    if state not in ("terminated"):
                        if args.verbose:
                            print "Terminating %s"%i
                        i.terminate()
                    else:
                        if args.verbose:
                            print "Not terminating %s"%i
    else:
        sys.stderr.write("No region specified\n")

if __name__ == "__main__":
    if TESTMODE:
        test()
        print "All tests passed"
        sys.exit(0)
    else:
        work(arguments(sys.argv[1:]))
