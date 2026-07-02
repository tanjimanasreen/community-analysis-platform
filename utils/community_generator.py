import networkx as nx
import pandas as pd
from utils.network_graph import *

def get_louvain_community(G, weight):
    communities = list(nx.community.louvain_communities(G, weight=weight, resolution=1, seed=123))
    partition = {node: idx for idx, community in enumerate(communities) for node in community}
    
    return communities, partition


# Get the prominent communities (have at lease min number of members) from the extracted louvain community

def detect_promiment_communities(communities, min_members):

    promiment_communities = [community for community in communities if len(community) >= min_members]
    # print(f"# of Communities with at least {min_members} memebers for Absolute Community: {len(promiment_communities_abs)}")   
    return promiment_communities


def get_promiment_communities(promiment_communities, G):
    community_number = 0
    community_data = {'source': [], 'target': [], 'community_number': [], 'direction': [], 'weight': []}
    
    for community in promiment_communities:

        subgraph = G.subgraph(community)
        edges = subgraph.edges(data=True)

        for edge in edges:
            source, target, data = edge
            direction = "Directed" if G.has_edge(source, target) else "Undirected"

            # print(f"Edge: {source} -> {target}, Weight: {data}, Direction: {direction}, Community: {community_number}")
            community_data['source'].append(source)
            community_data['target'].append(target)
            community_data['community_number'].append(community_number)
            community_data['direction'].append(direction)
            community_data['weight'].append(data)

        community_number += 1

    # Create DataFrame from the collected edge information
    df_community = pd.DataFrame(community_data)

    # Display the result DataFrame
    return df_community



def get_specific_community_info(df_community, community_number, df_network, df_user):
    total_msg = 0
    community = df_community[df_community['community_number'] == community_number]
    community_details = pd.DataFrame(columns=['producer_username', 'producer_user_id', 
                                              'forwarder_username', 'forwarder_user_id', 'total_messages', 
                                                  'messages', 'message_ids'])
    for index, row in community.iterrows():
        result_rows = df_network[(df_network['from_id'] == row['source']) & (df_network['forwarder_id'] == row['target'])]
        
        producer = df_user.loc[df_user['user_id'] == row['source'], ['username', 'user_id']].iloc[0].to_dict()
        producer_username = producer['username']
        producer_user_id = producer['user_id']
   
        forwarder =  df_user.loc[df_user['user_id'] == row['target'], ['username', 'user_id']].iloc[0].to_dict()
        forwarder_username = forwarder['username']
        forwarder_user_id = forwarder['user_id']
        
        messages = list(result_rows['text_translated'])
        total_msg+=len(messages)
        message_ids = list(result_rows['unique_id'])
        # channels = list(result_rows['to_id'])
        total_messages = len(messages)
        
        community_details = community_details.append({'producer_username': producer_username, 'producer_user_id': producer_user_id, 
                                              'forwarder_username': forwarder_username, 'forwarder_user_id': forwarder_user_id, 
                                                'total_messages': total_messages, 
                                                  'messages': messages, 'message_ids': message_ids
                                                    }, ignore_index=True)
        
        # print(f"Producer User: {producer_username, producer_user_id}, Forwarder User: {forwarder_username, forwarder_user_id}, # of Messages: {total_messages}\nMessages: {messages}, Channels: {channels}\n")
    
    # community_details['producer_username'] = community_details.apply(update_producer_username, axis=1)
    # community_details['forwarder_username'] = community_details.apply(update_forwarder_username, axis=1)
    
    return community_details


def get_community_messages(promiment_communities, community, df_network, df_user):
    community_messages = pd.DataFrame(columns=['community_number', 'messages', 'messages_ids', 'total_messages'])
    total_messages_count = 0
    for i in range(len(promiment_communities)):    
        specific_community_result = get_specific_community_info(community, i, df_network, df_user)
        # total_messages_count = total_messages_count + specific_community_result.total_messages.sum()
        
        community_messages = community_messages.append({'community_number': i, 'messages': specific_community_result.messages.sum(),
                                                                 'messages_ids' : specific_community_result.message_ids.sum(),
                                                                'total_messages': specific_community_result.total_messages.sum(),
                                                                }
                                                               ,ignore_index=True)
    
    return community_messages


def get_community_network_centrality(G, df_user):
    
    graph_info(G)
    
    result_out = show_hightest_out_degree(G, df_user)
    
    result_in = show_hightest_in_degree(G, df_user)

    return result_in | result_out

def get_prominent_communities_stat(prominent_communities, G, df_user):
    all_community_nodes = set().union(*prominent_communities)
    
    subgraph = G.subgraph(all_community_nodes)
    degree_result = get_community_network_centrality(subgraph, df_user)
    return degree_result



def get_overall_community_messages_stat(date_col, promiment_communities, df_community, df_network):

    community_messages_date = pd.DataFrame(columns=[date_col])

    for community_number in range(len(promiment_communities)):
        community = df_community[df_community['community_number'] == community_number]
        
        for index, row in community.iterrows():
            result_rows = df_network[(df_network['from_id'] == row['source']) & (df_network['forwarder_id'] == row['target'])]
    
            
            community_messages_date = community_messages_date.append(result_rows[[date_col]], 
                                                            ignore_index=True)
    
        
        community_messages_date['day'] = community_messages_date[date_col].apply(lambda x: eval(x)[2])
        
    
    month = eval(community_messages_date[date_col].iloc[0])[1]
    
    daily_messages = community_messages_date['day'].value_counts()
   
    min = daily_messages.min()
    day_of_min = daily_messages.idxmin()
    max = daily_messages.max()
    day_of_max = daily_messages.idxmax()
    
    total_messages = daily_messages.sum()
    total_days = len(daily_messages)
    avg_messages = daily_messages.mean()
    std_messages = daily_messages.std()

    # if month in [1, 3, 5, 7, 8, 10, 12]:
    #     days = 31
    #     avg_messages = total_messages/days
        
    # elif month in [4, 6, 9, 11]:
    #     days = 30
    #     avg_messages = total_messages/days
        
    # else:
    #     days = 28 
    #     avg_messages = total_messages/days
        
    messages_stat = {'min_msg_count': min, 'day_of_min_msg': day_of_min, 'max_msg_count': max, 'day_of_max_msg': day_of_max, 'std_msg_count': std_messages, 'avg_msg_count': avg_messages}                                                                           
   
    return messages_stat
