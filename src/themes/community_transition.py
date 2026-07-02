import pandas as pd
import ast

def jaccard_similarity(list1, list2):
    """Define Jaccard Similarity function for two sets"""
    set1 = set(list1) 
    set2 = set(list2)
    if not set1 and not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return float(intersection) / union

def find_matching_communities(df1: pd.DataFrame, df2: pd.DataFrame, month1: str, month2: str, content_type: str) -> pd.DataFrame:
    matched = []
    
    # Initialize lists to track unmatched communities if needed
    unmatched_df1 = df1['absolute_community'].tolist() if 'absolute_community' in df1.columns else []
    unmatched_df2 = df2['absolute_community'].tolist() if 'absolute_community' in df2.columns else []

    # Safe access functions since column names might vary or be missing
    def get_val(row, col, default=""):
        return str(row[col]) if col in row.index else default

    for index1, row1 in df1.iterrows():
        for index2, row2 in df2.iterrows():
            members1 = row1.get('members', [])
            members2 = row2.get('members', [])
            
            # Ensure members are lists
            if isinstance(members1, str):
                try: members1 = ast.literal_eval(members1)
                except: members1 = []
            if isinstance(members2, str):
                try: members2 = ast.literal_eval(members2)
                except: members2 = []

            jscore = jaccard_similarity(members1, members2)
            
            # Threshold of 0.0 for reply else 0.5
            threshold = 0.0 if (content_type == 'reply') else 0.5
            if threshold < jscore <= 1:
                common_members = list(set(members1) & set(members2)) 
                uncommon_members = list(set(members1) ^ set(members2))
                
                start_comm = row1.get('absolute_community', '0')
                end_comm = row2.get('absolute_community', '0')
                
                matched.append({
                    'start_month': month1,
                    'end_month': month2,
                    'start_month_community': f"{month1}_{start_comm}",
                    'end_month_community': f"{month2}_{end_comm}",
                    'jaccard_score': jscore,
                    'common_members': str(common_members),
                    'uncommon_members': str(uncommon_members),
                    'start_month_members': str(members1),
                    'total_start_month_members': len(members1),
                    'end_month_members': str(members2),
                    'total_end_month_members': len(members2),
                    'start_month_absolute_theme': get_val(row1, 'absolute_theme_names'),
                    'end_month_absolute_theme': get_val(row2, 'absolute_theme_names'),
                    'start_month_weighted_theme': get_val(row1, 'weighted_theme_names'),
                    'end_month_weighted_theme': get_val(row2, 'weighted_theme_names'),
                    'start_month_general_theme': get_val(row1, 'general_theme_names'),
                    'end_month_general_theme': get_val(row2, 'general_theme_names')
                })
                
                if start_comm in unmatched_df1:
                    unmatched_df1.remove(start_comm)
                if end_comm in unmatched_df2:
                    unmatched_df2.remove(end_comm)

    columns = ['start_month', 'end_month', 'start_month_community', 'end_month_community', 'jaccard_score', 
               'common_members', 'uncommon_members', 'start_month_members', 'total_start_month_members',
               'end_month_members', 'total_end_month_members', 'start_month_absolute_theme', 'end_month_absolute_theme',
               'start_month_weighted_theme', 'end_month_weighted_theme','start_month_general_theme', 'end_month_general_theme']
               
    matched_df = pd.DataFrame(matched, columns=columns)
    return matched_df

def get_community_transition(theme_dict: dict, content_type: str) -> pd.DataFrame:
    """
    Takes a dictionary of {month: df} sorted by month order.
    Calculates transitions for consecutive months.
    """
    all_matched = []
    month_names = list(theme_dict.keys())
    
    for i in range(1, len(month_names)): 
        m1 = month_names[i-1]
        m2 = month_names[i]
        result = find_matching_communities(theme_dict[m1], theme_dict[m2], m1, m2, content_type)
        if not result.empty:
            all_matched.append(result)
            
    if all_matched:
        matched_df = pd.concat(all_matched, ignore_index=True)
    else:
        # Return empty dataframe with correct columns
        columns = ['start_month', 'end_month', 'start_month_community', 'end_month_community', 'jaccard_score', 
                   'common_members', 'uncommon_members', 'start_month_members', 'total_start_month_members',
                   'end_month_members', 'total_end_month_members', 'start_month_absolute_theme', 'end_month_absolute_theme',
                   'start_month_weighted_theme', 'end_month_weighted_theme','start_month_general_theme', 'end_month_general_theme']
        matched_df = pd.DataFrame(columns=columns)
        
    return matched_df
