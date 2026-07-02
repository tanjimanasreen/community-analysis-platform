import pandas as pd
import ast, os
from dotenv import load_dotenv
import openai
from openai import OpenAI
from pathlib import Path
import time 
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import matplotlib.patches as patches
import numpy as np
from matplotlib.lines import Line2D
from collections import defaultdict

from sentence_transformers import SentenceTransformer, util
import seaborn as sns
from plotly.subplots import make_subplots
import plotly.io as pio
pio.templates.default = "plotly_white"

import json
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

load_dotenv()
api_key = os.environ.get('OPENAI_API_KEY')

openai.api_key = api_key
client = OpenAI()

# Initialize the model
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# A dictionary to convert month names to their respective orders
month_order = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12
}

# This function loads and prepares the final data we extracted from LDA analysis
def load_prepare_data(path_lda, year):
    
    month_names = []
    data_dict = {}

  
    for x in os.listdir(path_lda):
        if os.path.isfile(path_lda+x) and x.endswith(".csv"):
            month = month_names.append(x.split("_")[0])
                    
    
    # Sort the list by the month order using the dictionary
    month_names = sorted(month_names, key=lambda month: month_order[month.lower()])
    
    for month in month_names:
        month_df = pd.read_csv(path_lda+month+'_'+year+'.csv')
        data_dict[month] = month_df
    
    # Prepare the Keywords
    for month_name, month_df in data_dict.items():
    
        # Converting the columns back to list from string
        month_df.members = month_df.members.apply(ast.literal_eval)
        month_df.absolute_unigram_keywords = month_df.absolute_unigram_keywords.apply(ast.literal_eval)
        month_df.absolute_bigram_keywords = month_df.absolute_bigram_keywords.apply(ast.literal_eval)
        month_df.weighted_unigram_keywords = month_df.weighted_unigram_keywords.apply(ast.literal_eval)
        month_df.weighted_bigram_keywords = month_df.weighted_bigram_keywords.apply(ast.literal_eval)
    
        # Adding a new column which contains all the keywords
        month_df['all_keywords'] = month_df.absolute_unigram_keywords + month_df.absolute_bigram_keywords + month_df.weighted_unigram_keywords + month_df.weighted_bigram_keywords
    
        # Keeping only the unique Keywords
        month_df['all_keywords'] = month_df['all_keywords'].apply(lambda x: list(dict.fromkeys(x)))
    
        # Converting the Keywords list to a string
        month_df['all_keywords'] = month_df['all_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))
        
        # Adding a new columns with keywords from absolute group and weighted group
        month_df['absolute_keywords'] = month_df.absolute_unigram_keywords + month_df.absolute_bigram_keywords
        month_df['absolute_keywords'] = month_df['absolute_keywords'].apply(lambda x: list(dict.fromkeys(x)))
        month_df['absolute_keywords'] = month_df['absolute_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))
    
        month_df['weighted_keywords'] = month_df.weighted_unigram_keywords + month_df.weighted_bigram_keywords
        month_df['weighted_keywords'] = month_df['weighted_keywords'].apply(lambda x: list(dict.fromkeys(x)))
        month_df['weighted_keywords'] = month_df['weighted_keywords'].apply(lambda x: str(x).replace("[", "").replace("]", "").replace(" ", "").replace("'", ""))
    
    return data_dict

# The following three functions are used to call the GPT API and get the themes from the keywords       
def call_gpt_theme_api(text):

    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", 
             "content": """
            You are an expert who can find meaningful themes from a list of keywords, 
            that may contain specific events, people, locations, or topics.
            """},
        {"role": "user", "content": f'Based on the list of the keywords given below, provide only the exact theme and the corresponding keywords in a coherent short sentence in a JSON. The keys of the json should be theme names and values should be corresponding keywords. There could be one theme or multiple themes for each set of keywords. Here is the list of keywords: {text}'
        },
      ],
        seed = 42,
        temperature=0,
        response_format={ "type": "json_object" }
        
        # max_tokens=50,
        # top_p=1,
        # frequency_penalty=0,
        # presence_penalty=0 
    )
    # print(completion.system_fingerprint)
    
    parsed_theme = json.loads(completion.choices[0].message.content)
    
    return parsed_theme

def map_theme(community_value, reference_df, reference_community_column, theme_gpt, theme_names):
    for idx, row in reference_df.iterrows():
        if community_value in row[reference_community_column]:
            return pd.Series([row[theme_gpt], row[theme_names]])
    return pd.Series([None, None])
    
def generate_gpt_theme(path, dict_df):
    for month, month_df in dict_df.items():
        count = 0
    
        absolute_temp_df = month_df[['absolute_community', 'absolute_keywords']]
        absolute_grouped_df = absolute_temp_df.groupby('absolute_keywords').agg({'absolute_community': list}).reset_index()  
        
        weighted_temp_df = month_df[['weighted_community', 'weighted_keywords']]
        weighted_grouped_df = weighted_temp_df.groupby('weighted_keywords').agg({'weighted_community': list}).reset_index()  
    
        for ind, row in absolute_grouped_df.iterrows():
            time.sleep(2)
            gpt_result_abs = call_gpt_theme_api(row.absolute_keywords)
            absolute_grouped_df.at[ind, 'absolute_theme_gpt'] = str(gpt_result_abs)
            absolute_grouped_df.at[ind, 'absolute_theme_names'] = '.'.join(list(gpt_result_abs.keys()))
            
    
        for ind, row in weighted_grouped_df.iterrows():
            time.sleep(2)
            gpt_result_wei = call_gpt_theme_api(row.weighted_keywords)   
            weighted_grouped_df.at[ind, 'weighted_theme_gpt'] = str(gpt_result_wei)
            weighted_grouped_df.at[ind, 'weighted_theme_names'] = '.'.join(list(gpt_result_wei.keys()))
    
        
        for ind, row in month_df.iterrows():
            time.sleep(2)
            gpt_result = call_gpt_theme_api(row.all_keywords)
            month_df.at[ind, 'general_theme_gpt'] = str(gpt_result)
            month_df.at[ind, 'general_theme_names'] = '.'.join(list(gpt_result.keys()))
            
            count+=1
            print("Done Community: ", count)
            
        # Merge the themes
        month_df[['absolute_theme_gpt', 'absolute_theme_names']] = month_df['absolute_community'].apply(map_theme, args=(absolute_grouped_df, 'absolute_community', 'absolute_theme_gpt', 'absolute_theme_names' ))
        month_df[['weighted_theme_gpt', 'weighted_theme_names']] = month_df['weighted_community'].apply(map_theme, args=(weighted_grouped_df, 'weighted_community', 'weighted_theme_gpt', 'weighted_theme_names'))
    
        print("-------------- " + str(month) + " done with " + str(count) + " communities --------------")
        filename = str(month)+"_theme.csv"
        save_to = path / filename
        month_df.to_csv(save_to, index=False)

# This function loads the themes generated by GPT from the CSV files into a dictionary for further analysis
def load_theme_csv(path):
    month_names = []
    data_dict = {}
    
    for x in os.listdir(path):
        if os.path.isfile(path+x) and x.endswith(".csv"):
            month = month_names.append(x.split("_")[0])
            
    # Sort the list by the month order using the dictionary
    month_names = sorted(month_names, key=lambda month: month_order[month.lower()])
    
    for month in month_names:
        month_df = pd.read_csv(path+month+'_'+'theme.csv')
        month_df.members = month_df.members.apply(ast.literal_eval)
        
        data_dict[month] = month_df

    return data_dict

"""
 The following three functions are used to find the matching communities between two consecutive months to see 
 the transition of the communities
 The Jaccard Similarity function is used to find the similarity between two sets of members
"""

def jaccard_similarity(list1, list2):
    """Define Jaccard Similarity function for two sets"""
    set1 = set(list1) 
    set2 = set(list2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return float(intersection) / union

# This function finds the matching communities between two consecutive months
# It takes two dataframes, the month names, and the content type as input
# It returns a dataframe with the matching communities that exist over time and their details
def find_matching_communities(df1, df2, month1, month2, content_type):
    matched = []

    unmatched_df1 = df1['absolute_community'].tolist()
    unmatched_df2 = df2['absolute_community'].tolist()
    partial_matched = []
    # # Converting members column to sets for easy comparison
    # df1['members'] = df1['members'].apply(lambda x: set(x))
    # df2['members'] = df2['members'].apply(lambda x: set(x))

    # Finding matching communities
    for index1, row1 in df1.iterrows():
        for index2, row2 in df2.iterrows():
            
            jscore = jaccard_similarity(row1['members'], row2['members'])
            
            # Threshold of 0.0 for reply else 0.5
            threshold = 0.0 if (content_type == 'reply') else 0.5
            if threshold < jscore <= 1:
                common_members = list(set(row1['members']) & set(row2['members'])) 
                uncommon_members = list(set(row1['members']) ^ set(row2['members']))
                
                matched.append((month1, month2, month1+"_"+str(row1['absolute_community']), month2+"_"+str(row2['absolute_community']), jscore, common_members, uncommon_members, row1['members'], len(row1['members']), row2['members'], len(row2['members']), str(row1['absolute_theme_names']), str(row2['absolute_theme_names']), str(row1['weighted_theme_names']), str(row2['weighted_theme_names']), str(row1['general_theme_names']), str(row2['general_theme_names'])))
                if row1['absolute_community'] in unmatched_df1:
                    unmatched_df1.remove(row1['absolute_community'])
                if row2['absolute_community'] in unmatched_df2:
                    unmatched_df2.remove(row2['absolute_community'])
           
                    
    # Create dataframes for matched and unmatched communities
    matched_df = pd.DataFrame(matched, columns=['start_month', 'end_month', 'start_month_community', 'end_month_community', 'jaccard_score', 
                                                'common_members', 'uncommon_members', 'start_month_members', 'total_start_month_members',
                                                'end_month_members', 'total_end_month_members', 'start_month_absolute_theme', 'end_month_absolute_theme',
                                               'start_month_weighted_theme', 'end_month_weighted_theme','start_month_general_theme', 'end_month_general_theme'])
    # partial_matched = pd.DataFrame(partial_matched, columns=[month1, month1+'_members', month2, month2+'_members', 'jaccard_score', 'common_members', 'uncommon_members'])

    unmatched_df1 = pd.DataFrame(unmatched_df1, columns=[month1])
    unmatched_df2 = pd.DataFrame(unmatched_df2, columns=[month2])
    
    return matched_df

def get_community_transition(path, theme_df, content_type):

    matched_df = pd.DataFrame(columns=['start_month', 'end_month', 'start_month_community', 'end_month_community', 'jaccard_score', 
                                                    'common_members', 'uncommon_members', 'start_month_members', 'total_start_month_members', 
                                                    'end_month_members', 'total_end_month_members',
                                                    'start_month_absolute_theme', 'end_month_absolute_theme',
                                                   'start_month_weighted_theme', 'end_month_weighted_theme',
                                       'start_month_general_theme', 'end_month_general_theme'])
    
    month_names = list(theme_df.keys()) 
    
    for i in range(1, len(theme_df)): 
        result = find_matching_communities(theme_df[month_names[i-1]], theme_df[month_names[i]], month_names[i-1], month_names[i], content_type)
        matched_df = matched_df.append(result, ignore_index=True)
    
    filename = "community_transition.csv"
    save_to = path / filename
    matched_df.to_csv(save_to, index=False)

    return matched_df


# This function takes the matched dataframe and extracts the source and target indices for the Sankey diagram for community transitions over time
def get_path_info(matched_df):

    all_community = list(matched_df.start_month_community) + list(matched_df.end_month_community)
    all_community = list(set(all_community))
    source_ind = []
    target_ind = []
    score = []
    for ind, row in matched_df.iterrows():
    
        source_ind.append(all_community.index(row.start_month_community))
        target_ind.append(all_community.index(row.end_month_community))
        score.append(row.jaccard_score)

    return source_ind, target_ind, score, all_community


def draw_community_transition_diagram(file_path, source_ind, target_ind, score, all_community, matched_df):
        
    # Define color palette (shades of blue and purple) for nodes
    month_colors = {
        'january': "rgba(31, 119, 180, 0.8)",
        'february': "rgba(174, 199, 232, 0.8)",
        'march': "rgba(44, 160, 44, 0.8)",
        'april': "rgba(152, 223, 138, 0.8)",
        'may': "rgba(255, 127, 14, 0.8)",
        'june': "rgba(255, 187, 120, 0.8)",
        'july': "rgba(214, 39, 40, 0.8)",
        'august': "rgba(255, 152, 150, 0.8)",
        'september': "rgba(148, 103, 189, 0.8)",
        'october': "rgba(197, 176, 213, 0.8)"
    }
    
    # Assign node colors based on their month
    node_colors = [month_colors[label.split('_')[0]] for label in all_community]
    
    # Scale the score into grayscale values for link colors
    max_gray, min_gray = 105, 220
    gray_values = [int(min_gray + (max_gray - min_gray) * ((s - min(score)) / (max(score) - min(score)))) for s in score]
    link_colors = [f"rgba({gray}, {gray}, {gray}, 0.9)" for gray in gray_values]
    
    # Define x positions based on months
    months_order = {
        'january': 0.1, 'february': 0.2, 'march': 0.3, 'april': 0.4,
        'may': 0.5, 'june': 0.6, 'july': 0.7, 'august': 0.8,
        'september': 0.9, 'october': 1.0
    }
    node_positions_x = [months_order[label.split('_')[0]] for label in all_community]
    node_positions_y = [0.9 - (i / len(all_community)) for i in range(len(all_community))]  # Distribute vertically

    # Community and member labels
    community_and_members = []
    for com in all_community:
        if len(matched_df[matched_df.start_month_community == com].start_month_members.to_list()) != 0:
            members = ast.literal_eval(matched_df[matched_df.start_month_community == com].start_month_members.to_list()[0]) if isinstance(matched_df[matched_df.start_month_community == com].start_month_members.to_list()[0], str) else matched_df[matched_df.start_month_community == com].start_month_members.to_list()[0]
            community_and_members.append((com, "Members: " + str(len(members))))
        else:
            members = ast.literal_eval(matched_df[matched_df.end_month_community == com].end_month_members.to_list()[0]) if isinstance(matched_df[matched_df.end_month_community == com].end_month_members.to_list()[0], str) else matched_df[matched_df.end_month_community == com].end_month_members.to_list()[0]
            community_and_members.append((com, "Members: " + str(len(members))))

    # print(community_and_members)
    # Create the Sankey diagram with custom node positions
    sankey = go.Sankey(
        valueformat=".1f",
        node=dict(
            pad=15,
            thickness=30,  # Increase node thickness
            label=community_and_members,
            color=node_colors,
            x=node_positions_x,
            y=node_positions_y
        ),
        link=dict(
            arrowlen=15,
            source=source_ind,
            target=target_ind,
            value=score,
            color=link_colors,
            hovertemplate='Source: %{source.label}<br>Target: %{target.label}<br>Value: %{value:.1f}<extra></extra>'
        )
    )

    # Create color bar legend using `Scatter` to represent the score gradient
    color_legend = go.Scatter(
        # x=[min(score), max(score)],  # Display the min and max scores on x-axis
        # y=[0, 0],  # Keep the y-axis constant
        x=[None],  # Use None to prevent plotting points
        y=[None],  # Prevent plotting points
        mode='markers',
        marker=dict(
            size=20,
            cmin=min(score),
            cmax=max(score),
            color=[min_gray, max_gray],
            colorscale='Greys',
            showscale=True,
            colorbar=dict(
                title="Score",
                thickness=15,
                orientation="h",  # Make the color bar horizontal
                xanchor="center",  # Align the color bar in the center
                x=0.5,  # Adjust the horizontal position of the color bar
                y=-0.1,  # Adjust the vertical position of the color bar (below the chart)
                tickvals=[min(score), max(score)],  # Show only min and max score values
                ticktext=[f"{min(score):.2f}", f"{max(score):.2f}"]  # Format tick labels
            ),
        ),
        showlegend=False
    )

    # Combine Sankey trace and color legend
    fig = go.Figure(data=[sankey, color_legend])
    
    # Layout settings
    fig.update_layout(
        font_size=12,
        width=1000,  # Increase figure width
        height=800,  # Increase figure height
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # Remove grid lines
    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False, visible=False)
    
    # Display the figure
    fig.show()
    # Save the figure as an image and HTML file
    filename = "community_transition.png"
    fig.write_image(file_path / filename)
    html_file = "community_transition.html"
    fig.write_html(file_path / html_file)


# The folowing three functions are used to build a directed graph and find all paths 
# between start and end nodes so thst we could extract the paths from the sankey diagram
# which are used to see the transitions of members between the communities that existed over time
def build_graph(source_ind, target_ind):
    """Builds a directed graph and identifies start and end nodes."""
    graph = defaultdict(list)
    out_degrees = defaultdict(int)
    in_degrees = defaultdict(int)
    
    for src, tgt in zip(source_ind, target_ind):
        graph[src].append(tgt)
        out_degrees[src] += 1
        in_degrees[tgt] += 1
        if tgt not in out_degrees:
            out_degrees[tgt] = 0
        if src not in in_degrees:
            in_degrees[src] = 0
            
    start_nodes = [node for node in out_degrees if in_degrees[node] == 0]
    end_nodes = [node for node in out_degrees if out_degrees[node] == 0]
    return graph, start_nodes, end_nodes


def dfs_all_paths(graph, start, end, path=None):
    """Recursive DFS to find all paths from start to end."""
    if path is None:
        path = []
    path = path + [start]
    
    if start == end:
        return [path]
    if start not in graph:
        return []
    
    paths = []
    for next_node in graph[start]:
        if next_node not in path:
            new_paths = dfs_all_paths(graph, next_node, end, path)
            for new_path in new_paths:
                paths.append(new_path)
    return paths


def find_all_sankey_paths(source_ind, target_ind, all_community):
    """Finds all paths from all start nodes to all end nodes."""
    graph, start_nodes, end_nodes = build_graph(source_ind, target_ind)
    all_paths = []
    for start in start_nodes:
        for end in end_nodes:
            paths = dfs_all_paths(graph, start, end)
            for path in paths:
                # Convert indices to community names
                all_paths.append([all_community[node] for node in path])
    return all_paths


# The following two function are used to calculate the membership changes over time and provide the diagrams
def calculate_membership_changes(communities):
    results = {}
    prev_members = set()

    for month, members in communities.items():
        current_members = set(members)
        
        if len(prev_members) == 0:
            new_members = set()  # No new members in the first month, as there is no previous month to compare.
            lost_members = set()  # No lost members in the first month.
        else:
            new_members = current_members - prev_members  # New members are those in current but not in previous.
            lost_members = prev_members - current_members  # Lost members are those in previous but not in current.

        # Store results including both new members and members who have left
        results[month] = {
            'members': list(current_members),
            'new_members': list(new_members),
            'lost_members': list(lost_members)
        }
        
        # Update previous members set for next iteration
        prev_members = current_members

    return results


def draw_members_transition_diagram(file_path, paths, matched_df):
    all_comm = {}
    count = 1
    for path in paths:
        comm = {}
        for p in path:
            if len(matched_df[matched_df.start_month_community == p].start_month_absolute_theme.values) != 0:
                members = ast.literal_eval(matched_df[matched_df.start_month_community == p].start_month_members.values[0]) if isinstance(matched_df[matched_df.start_month_community == p].start_month_members.values[0], str) else matched_df[matched_df.start_month_community == p].start_month_members.values[0]
                comm[p]= members
            else:
                members = ast.literal_eval(matched_df[matched_df.end_month_community == p].end_month_members.values[0]) if isinstance(matched_df[matched_df.end_month_community == p].end_month_members.values[0], str) else matched_df[matched_df.end_month_community == p].end_month_members.values[0]
                comm[p] = members
        all_comm[count] = comm
        count+=1
        
    # Calculate membership changes
    for i in range(1, len(all_comm)+1):
        membership_changes = calculate_membership_changes(all_comm[i])
    
        # Dynamic figure size based on number of months and members
        fig, axs = plt.subplots(1, len(membership_changes), figsize=(10 * len(membership_changes), 10))
    
        all_members = []
        prev_ax = None
        
        for ax, (month, data) in zip(axs, membership_changes.items()):
            num_members = len(data['members'])
            
            # Set circle size based on number of members (more members, smaller circles)
            circle_size = max(0.04, min(0.06, 0.2 / num_members))  # Adjust the size dynamically
            
            # Improved grid layout to prevent overlaps with more spacing
            grid_size = int(np.ceil(np.sqrt(num_members)))
            layout_radius = 0.2 * grid_size  # Increase the layout spacing

            # Calculate grid positions with increased padding
            spacing = 0.8 / grid_size
            member_positions = {
                member: (0.5 + (i % grid_size - grid_size // 2) * spacing, 
                         0.5 + (i // grid_size - grid_size // 2) * spacing)
                for i, member in enumerate(data['members'])
            }
            
            for member, pos in member_positions.items():
                # Determine color based on whether the member is new
                if member not in data['new_members']:
                    color = 'green'  # Existing members
                else:
                    if member in all_members:
                        color = 'grey'  # Repeating members
                    else:
                        color = 'red'  # New members
                
                # Use smaller circles for large numbers of members
                member_circle = patches.Circle(pos, circle_size, edgecolor='black', facecolor=color, linewidth=1.5)
                ax.add_patch(member_circle)
                
                
            all_members += data['members']
            
            # Draw connection arrow to previous month
            if prev_ax is not None:
                con = patches.ConnectionPatch(xyA=(1.0, 0.5), xyB=(0.01, 0.5), coordsA='axes fraction', coordsB='axes fraction',
                                              axesA=prev_ax, axesB=ax, arrowstyle='simple', linestyle='-', color='black', linewidth=1)
                fig.add_artist(con)
        
            prev_ax = ax
        
            # Set up plot
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            ax.set_title(month, fontsize=14)
        
        # Create legend for member colors, move it outside the grid
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Existing Member'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='New Member'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='grey', markersize=10, label='Reappearing Member')
        ]
        fig.legend(handles=legend_elements, loc='upper left', fontsize=10, title="Member Status", bbox_to_anchor=(1.05, 1))
        
        # Adjust spacing between subplots and save the plot
        fig.subplots_adjust(wspace=1) 
        plt.tight_layout()
        filename = 'community_changes_' + str(i) + '.png'
        save_file_path = file_path / filename
        plt.savefig(save_file_path, dpi=600, transparent=True)
        plt.show()

# The following three fucntions are used to calculated the similarity between the themes of the  similar communities that existed over time
# This function calculates the cosine similarity between sentences using the SentenceTransformer model
def calculate_sentence_similarity(sentences):
    # Encode sentences and calculate cosine similarity matrix
    embeddings = model.encode(sentences, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(embeddings, embeddings).cpu().numpy()
    return cosine_scores


def extract_themes(matched_df, paths, start_month_theme, end_month_theme):
    all_community_theme = {}
    count = 1
    
    for path in paths:
        themes = {}
        for p in path:
            if len(matched_df[matched_df.start_month_community == p][start_month_theme].values) != 0:
                # Use the passed 'start_month_theme' argument to extract theme
                themes[p] = matched_df[matched_df.start_month_community == p][start_month_theme].values[0]
            else:
                # Use the passed 'end_month_theme' argument to extract theme
                themes[p] = matched_df[matched_df.end_month_community == p][end_month_theme].values[0]
        
        all_community_theme[count] = themes
        count += 1

    return all_community_theme


def draw_theme_similarity_heatmap(all_community_theme, file_path, file_name):
    
    # Determine the layout of the subplots
    num_sets = len(all_community_theme)
    cols = 3  # Adjust the number of columns based on your preference
    rows = (num_sets + cols - 1) // cols  # Calculate required rows to fit all sets
    
    # Create a figure with subplots in Plotly
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=[f'Community Set {i}' for i in range(1, num_sets + 1)],
                        horizontal_spacing=0.1, vertical_spacing=0.1)

    max_similarity = -np.inf
    min_similarity = np.inf

    # First pass to find the global min and max for the color scale
    for communities in all_community_theme.values():
        themes = list(communities.values())
        similarity_matrix = calculate_sentence_similarity(themes)
        max_similarity = max(max_similarity, np.max(similarity_matrix))
        min_similarity = min(min_similarity, np.min(similarity_matrix))

    # Second pass to add half heatmaps to the figure
    for index, (community_set_number, communities) in enumerate(all_community_theme.items()):
        themes = list(communities.values())
        community_names = list(communities.keys())
    
        # Calculate similarities
        similarity_matrix = calculate_sentence_similarity(themes)

        # Mask the lower triangle by setting the lower triangle values to NaN
        mask = np.tril(np.ones(similarity_matrix.shape, dtype=bool))
        similarity_matrix = np.where(mask, np.nan, similarity_matrix)
        
        row = index // cols + 1
        col = index % cols + 1

        # Create a half heatmap using Plotly
        fig.add_trace(
            go.Heatmap(
                z=similarity_matrix,
                x=community_names,
                y=community_names,
                colorscale='bluyl',
                zmin=min_similarity,
                zmax=max_similarity,
                showscale=False,  # Turn off the individual scale for each plot
                texttemplate="%{z:.2f}",
                hoverongaps=False,
                zauto=False 
            ),
            row=row, col=col
        )
    
    # Update layout for consistent color scale
    fig.update_layout(
        title_text=f'Cosine Similarity Score between the Similar Communities Theme ({file_name})',
        height=rows * 360,  # Adjust height based on number of rows
        width=cols * 360,   # Adjust width based on number of columns
        coloraxis_colorbar=dict(
            title="Score",
            tickvals=[min_similarity, max_similarity],
            ticktext=[f'{min_similarity:.2f}', f'{max_similarity:.2f}'],
            lenmode="fraction",
            len=0.3,  # Adjust the size of the color bar
            yanchor="middle",  # Align it in the middle
            y=0.4
        )     
    )

    # Add a single color scale for all subplots
    for trace in fig.data:
        trace['coloraxis'] = 'coloraxis'
    
    # Show the plot
    fig.show()
    filename = file_name+".png"
    save_to_path = file_path / filename
    fig.write_image(save_to_path, scale=2)



def main():
    # The base parameters for the analysis
    # path = 'telegram/LDA/'
    # year = '2019'
    # data_type = 'telegram'
    data_type = 'twitter'
    path = data_type + '/LDA/'
    year = '2017' 
    content_type = 'mixed'

    #Load the data
    monthly_data_dict = load_prepare_data(path+'matched/'+content_type+'/', year)
    print(monthly_data_dict)      

    # Generate the themes from the LDA keywords using GPT
    generated_theme_path = Path(path + 'matched_theme/') / content_type
    generated_theme_path.mkdir(parents=True, exist_ok=True)
    generate_gpt_theme(generated_theme_path, monthly_data_dict)

    # Load the themes data
    theme_df = load_theme_csv(path+'matched_theme/'+content_type+'/')
    print(theme_df)

    # Get the community transition
    community_transition_path = Path(path + 'community_transition/') / content_type
    community_transition_path.mkdir(parents=True, exist_ok=True)
    print(community_transition_path)

    matched_df = get_community_transition(community_transition_path, theme_df, content_type)
    matched_df = pd.read_csv(community_transition_path/'community_transition.csv')
    print(matched_df.head())

    # Draw the community transition diagram
    source_ind, target_ind, score, all_community = get_path_info(matched_df)
    draw_community_transition_diagram(community_transition_path, source_ind, target_ind, score, all_community, matched_df)

    # Find all paths in the Sankey diagram
    paths_detected = find_all_sankey_paths(source_ind, target_ind, all_community)

    # Find and Draw the membership transition diagram
    membership_change_path = Path(path + 'membership_change_graphs/') / content_type
    membership_change_path.mkdir(parents=True, exist_ok=True)
    draw_members_transition_diagram(membership_change_path, paths_detected, matched_df)

    # Find and Draw the theme similarity heatmap
    theme_similarity_path = Path(path + 'theme_similarity/') / content_type
    theme_similarity_path.mkdir(parents=True, exist_ok=True)
    # absolute themes
    community_absolute_themes = extract_themes(matched_df, paths_detected, 'start_month_absolute_theme', 'end_month_absolute_theme')
    draw_theme_similarity_heatmap(community_absolute_themes, theme_similarity_path, 'absolute_theme')
    # weighted themes
    community_weighted_themes = extract_themes(matched_df, paths_detected, 'start_month_weighted_theme', 'end_month_weighted_theme')
    draw_theme_similarity_heatmap(community_weighted_themes, theme_similarity_path, 'weighted_theme')
    # general themes
    community_general_themes = extract_themes(matched_df, paths_detected, 'start_month_general_theme', 'end_month_general_theme')
    draw_theme_similarity_heatmap(community_general_themes, theme_similarity_path, 'general_theme')

if __name__ == "__main__":
    main()