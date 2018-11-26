# coding=utf-8
# Licensed Materials - Property of IBM
# Copyright IBM Corp. 2017
"""
Monitor shipboard reefers (refrigerated containers) traveling over blue water.

*****
NOTES
*****

- Pushing data to redis in order that something viewport into the processing.
- Sample record
   type: <class 'dict'>
   data: {'id': 'Reefer_5', 'ts': '2018-01-01 21:44:00',
       'oTemp': 22.1,
       'latitude': 10.11291508, 'longitude': 83.09646606,
       'amp': 55.730234304187434, 'tempC': 1.974183120145919}

"""

import common
import credential
import argparse
from streamsx.topology.schema import *
from streamsx.topology.topology import Topology
from streamsx.topology.schema import CommonSchema
import streamsx.messagehub
from pathlib import Path
from resourceAccess import TransmitRedis


class ExampleMap(object):
    def __init__(self, val_var):
        self.valvar = val_var
        pass

    def __call__(self, dct):
        print("type:", type(dct))
        print("data:", dct)
        return dct


def monitor(job_name, name_space, mh_topic, redis_base=None):
    topo = Topology(job_name, name_space)
    topo.add_pip_package('streamsx.messagehub')

    fromMh = streamsx.messagehub.subscribe(topo, schema=CommonSchema.Json, topic=mh_topic)

    exampleMap = fromMh.map(ExampleMap(val_var=10), name="examMap")
    filterTest = exampleMap.filter(lambda t: t['id'].startswith("Reefer_"), name="filterTest")
    filterLambda = filterTest.filter(lambda t: t['id'] is not None, name="anaTest")
    # mapLambda = filterLambda.map(lambda t: dict((k, t[k]) for k in ("id", "oTemp")))
    filterLambda.sink(TransmitRedis(credentials=credential.redisCredential,
                                     dest_key=redis_base + "/bluewater", chunk_count=10000))
    return topo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reefer Monitor')
    parser.add_argument('--pwd', help="password to decrypyt credential file", default=None)
    parser.add_argument('--streamsService', help="Name of the Streams Analytics service", default="Streaming3Turbine")
    parser.add_argument('--serviceType', help="Type of service to build: STREAMING_ANALYTICS, BUILD_ARCHIVE.",
                        default="STREAMING_ANALYTICS")
    parser.add_argument('--buildType',
                        help="Either 'DISTRIBUTED' or 'BUNDLE' determines if scripts+submit or just scripts.",
                        default="DISTRIBUTED")
    defJobName = Path(parser.prog).resolve().stem
    parser.add_argument('--jobName', help="Name to assign to the job name", default=defJobName)
    parser.add_argument('--nameSpace', help="Name to assign to the namespace", default=defJobName)
    parser.add_argument('--cancel', help="Cancel active job before submitting job, uses jobName, nameSpace",
                        default=True)
    # application specfic arguments...
    parser.add_argument('--mhTopic', help="MessageHub topic to to send ekg events out on.", default="jsonEvents")
    parser.add_argument('--redisBase', help="Redis monitor path base path.", default="/score")

    args = parser.parse_args()

    topology = monitor(job_name=args.jobName, name_space=args.nameSpace,
                   mh_topic=args.mhTopic, redis_base=args.redisBase)

    try:
        import creds.credential as creds
    except ImportError:
        common.decryptCredentials(zipPath="../shared/creds/", cryptFile="credential.py.zip",
                                  decryptFile='credential.py', pwd=args.pwd)
        import creds.credential as creds
    submitStatus = common.submitProcess(topology=topology,
                                        streamsService=args.streamsService,
          buildType=args.buildType,
          serviceType=args.serviceType,
          jobName=args.jobName,
          cancel=args.cancel, )
    print("Process status:%s" % submitStatus)
