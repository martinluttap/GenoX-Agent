import requests,os
import math
import random
import time
import numpy as np
import sys
from threading import Thread
from multiprocessing import Process,Manager
import argparse
import subprocess
import pandas
import json

parser = argparse.ArgumentParser(description='--head,--qps,--node_size')
 
parser.add_argument('-head','--head', type=int, default=1)
parser.add_argument('-q','--qps', type=int, default=3750)
parser.add_argument('-n','--node_size', type=int, default=1)
parser.add_argument('-d','--duration', type=int, default=30)
parser.add_argument('-p','--process', type=int, default=1)
parser.add_argument('-t','--types', type=int, default=4)
parser.add_argument('-nodeName','--nodeName', type=str, default='cpu-02')

cg_rate_list_all=[  
                  [],
                  [1,1,1,1,1],
                  [0.5,0.5,1,1,2],
                  [0.5,0.5,1.5,0.5,2],
                  [1,0.5,1,0.5,2],
                  [1.5,0.5,0.5,0.5,2]]
cg_rate_list=[]

data="http://node1.nodens-8-rs630.sosp24ae-pg0.cloudlab.umass.edu:30001/"
node_list=[
    'node1.nodens-8-rs630.sosp24ae-pg0.cloudlab.umass.edu',
    # 'node2.nodens-8-rs630.sosp24ae-pg0.cloudlab.umass.edu',
    # 'node3.nodens-8-rs630.sosp24ae-pg0.cloudlab.umass.edu',
    # 'node4.nodens-8-rs630.sosp24ae-pg0.cloudlab.umass.edu',
]

def search(dynamic_rate):
    # random data generation
    in_date=random.randint(9,23)
    # out_date=random.randint(in_date+1,24)
    out_date=in_date+1
    in_date_str=str(in_date)
    if(in_date<=9):
        in_date_str="2015-04-0"+in_date_str
    else:
        in_date_str="2015-04-"+in_date_str
    out_date_str=str(out_date)
    if(out_date<=9):
        out_date_str="2015-04-0"+out_date_str
    else:
        out_date_str="2015-04-"+out_date_str
    lat = 38.0235 + (random.uniform(0, 481) - 240.5)/1000.0
    lon = -122.095 + (random.uniform(0, 325) - 157.0)/1000.0
    # req_param="rates"
    coin=random.random()
    if(coin<dynamic_rate):# search by distance
        req_param="nearby"
    else:#search by rate
        req_param="rates"
    # else:           #search by rate in certain disctance
    #     req_param="all"
    # generate url and params
    url=data+"hotels"
    params={
        "inDate":in_date_str,
        "outDate":out_date_str,
        "lat":str(lat),
        "lon":str(lon),
        "require":req_param,
    }
    return url,params

#hotel-benchmark "recommend" generate url with random data
def recommend(dynamic_rate):
    # random data generation
    coin=random.random()
    if coin<dynamic_rate:
        coin_=random.random()
        if(coin_<0.33):# best fit shortest distance
            req_param="dis"
        elif(coin_<0.66):#best fit hightest rate
            req_param="rate"
        else:#best fit lowest price
            req_param="price"
        lat = 38.0235 + (random.uniform(0, 481) - 240.5)/1000.0
        lon = -122.095 + (random.uniform(0, 325) - 157.0)/1000.0
        # generate url and params
        url=data+"recommendations"
        params={
            "require":str(req_param),
            "lat":str(lat),
            "lon":str(lon)
        }
    else:
        req_param="overall"
        lat = 38.0235 + (random.uniform(0, 481) - 240.5)/1000.0
        lon = -122.095 + (random.uniform(0, 325) - 157.0)/1000.0
        id = random.randint(0, 500)
        user_name = "Cornell_"+str(id)
        # generate url and params
        url=data+"recommendations"
        params={
            "require":str(req_param),
            "lat":str(lat),
            "lon":str(lon),
            "username":user_name
        }        
    return url, params

#hotel-benchmark "user" generate url with random data
def user():
    # random data generation
    id = random.randint(0, 500)
    user_name = "Cornell_"+str(id)
    pass_word = ""
    for i in range(3):
        pass_word=pass_word+str(id)
    # generate url and params
    url=data+"user"
    params={
        "username":str(user_name),
        "password":str(pass_word)
    }
    return url, params

#hotel-benchmark "reserve" generate url with random data
def reserve():
    # random data generation
    in_date=random.randint(9,23)
    out_date=in_date+random.randint(1,5)
    in_date_str=str(in_date)
    if(in_date<=9):
        in_date_str = "2015-04-0"+in_date_str 
    else:
        in_date_str = "2015-04-"+in_date_str
    out_date_str=str(out_date)
    if(out_date<=9):
        out_date_str = "2015-04-0"+out_date_str 
    else:
        out_date_str = "2015-04-"+out_date_str
    hotel_id=str(random.randint(1,80))
    id = random.randint(0, 500)
    user_name = "Cornell_"+str(id)
    pass_word = ""
    for i in range(10):
        pass_word=pass_word+str(id)
    cust_name=user_name
    num_room="1"
    # generate url and params
    url=data+"reservation"
    params={
        "inDate":in_date_str,
        "outDate":out_date_str,
        "lat":"",
        "lon":"",
        "hotelId":hotel_id,
        "customerName":cust_name,
        "username":user_name,
        "password":pass_word,
        "number":num_room
    }
    return url, params

def generate_gaussian_arraival():
    dis_list = np.random.normal(4,0.08,250)#mu,sigma,sampleNo
    # dis_list=[]
    # with open("GD_norm.csv") as f:#use already generated data before
    #     for line in f:
    #         dis_list.append(float(line.replace("\n","")))
    return dis_list

#post a request
def post_request(url, params,list_99):
    response=requests.get(url=url,params=params,headers={'Connection':'close'},timeout=(10,10))
    # print(f'{args.nodeName}: {response.url}')
    list_99.append([time.time(),response.elapsed.total_seconds()*1000])

# generate requests with dynamic graphs
def dynamic_graph_rate(dr0,dr1,dr2,dr3,dr4):
    # ratio for 3 kinds of call graphs
    cnt=dr0+dr1+dr2+dr3+dr4
    search_ratio=float(dr0+dr1)/cnt
    recommend_ratio=float(dr2+dr3)/cnt
    reserve_ratio=float(dr4)/cnt
    # for each request, random call graph
    # print(search_ratio,recommend_ratio,reserve_ratio)
    coin=random.random()
    if(coin<search_ratio):
        url, params=search(float(dr0)/(dr0+dr1))
    elif(coin<search_ratio+recommend_ratio):
        url, params=recommend(float(dr2)/(dr2+dr3))
    else:
        url, params=reserve()
    return url, params

def threads_generation(QPS_list,duraion,process_number,list_99_all): #250,20
    plist = []
    query_list = []
    dis_list = []
    list_99=[]
    gs_inter=generate_gaussian_arraival()
    print(f'{args.nodeName}: {gs_inter}, QPS_list={QPS_list}')
    for j in range(0,duraion):
        QOS_this_s=int(QPS_list[j]/process_num)
        for i in range(0,QOS_this_s):
            url, params=dynamic_graph_rate(cg_rate_list[0],cg_rate_list[1],
            cg_rate_list[2],cg_rate_list[3],cg_rate_list[4])#determine dynamic call graph
            params_json = json.dumps(params)
            print(f'{args.nodeName}[j={j}/{duraion}][i={i}/{QOS_this_s}]: posting to url={url},params={params},len_list99={len(list_99)}')
            p = Thread(target=post_request,args=(url,params,list_99))
            plist.append(p)
            dis_list.append(gs_inter[i%250]* 250/QOS_this_s)
    # print("Total %d thread in %d s"%(len(dis_list),duraion))
    fun_sleep_overhead=0.000075# overhead to call sleep()function
    # print("begin")
    # For each process, control the QPS=250query/s, and apply Gaussian distribution
    waste_time=0
    t1=time.time()
    for i in range(len(plist)):
        t_s=time.time()#10^-3ms, negligible
        plist[i].start()
        t_e=time.time()
        #[thread start time] + [sleep() funtion time] + [sleep time] = dis_list[i]
        sleep_time=dis_list[i]/1000-((t_e-t_s)+fun_sleep_overhead)
        if(sleep_time>0):
            # can compensate
            if(sleep_time+waste_time>=0):
                time.sleep(sleep_time+waste_time)
                waste_time=0
            else:
                waste_time+=sleep_time
        else:
            waste_time+=sleep_time
    t2=time.time()
    print("done, time count is %f,should be %d, waste_time %f\n"%(t2-t1,duraion,waste_time))
    #Control all the requests ends before statistics
    for item in plist:
        item.join()
    list_99_all.append(list_99)
    # print(np.percentile(np.array(list_99),99))

def request_test(QPS_list,duraion=20,process_number=1):
    print(f'{args.nodeName} in request_test')
    time1=time.time()
    assert len(QPS_list)==int(duraion)
    process_list=[]
    list_99_all=Manager().list()
    for i in range(process_number):
        p=Process(target=threads_generation,args=(QPS_list,duraion,process_number,list_99_all))
        process_list.append(p)
    # start processes
    for p in process_list:
        p.start()
    # print("All processes start.")
    for p in process_list:
        p.join()
    print("All processes done.Total is %f"%(time.time()-time1))    
    latency_this_node=[]
    print(f'Collecting latency ...')
    for i in list_99_all:
        latency_this_node.extend(i)
    for i in range(len(latency_this_node)):
        latency_this_node[i][0]-=time1
    latency_this_node=sorted(latency_this_node,key=(lambda x:x[0]),reverse=False)  
    df=pandas.DataFrame(latency_this_node,columns=['time','latency'])
    df.to_csv(f'hr_{args.nodeName}_latency.csv') 
            
def run_on_node(cmd):
    os.system(cmd)

if __name__ == "__main__":
    args = parser.parse_args()
    print(f'Invoked with: {args}')
    if args.head:
        o_process_list=[]
        for i in range(args.node_size):
            cmd=f" ssh {node_list[i]} 'ulimit -n 100000;cd /root/2024-ec-nodens/Nodens/LoadGenerator; TS=$(date \"+%d/%m/%Y %H:%M:%S\") ; echo $TS > ts.txt ; python3 LoadGenerator-dis-hr.py --head {0} --qps {args.qps} --node_size {args.node_size} -p {args.process} -t {args.types} -nodeName {node_list[i]} -d {args.duration} | tee /root/nonhead.txt' "
            print(cmd)
            # run_on_node(cmd)
            p=Process(target=run_on_node,args=(cmd,))
            o_process_list.append(p)
        for p in o_process_list:
            p.start()
        for p in o_process_list:
            p.join()
    else:
        print(args)
        os.system("ulimit -n 100000")
        QPS=int(args.qps/args.node_size)
        duraion=args.duration
        process_num=args.process
        cg_rate_list=cg_rate_list_all[args.types]
        QPS_list=[]
        for i in range(duraion):
            QPS_list+=[QPS]
        # print(QPS_list)
        request_test(QPS_list,duraion,process_num)