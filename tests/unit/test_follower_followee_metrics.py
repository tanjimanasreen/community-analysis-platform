import pytest
import pandas as pd
from src.network.follower_followee import extract_network_structure, get_follower_followee_network

def test_extract_network_structure():
    df_network = pd.DataFrame({
        'from_id': ['u1', 'u1', 'u1', 'u1', 'u2'],
        'forwarder_id': ['u2', 'u3', 'u2', 'u1', 'u1']
    })
    
    result = extract_network_structure(df_network, 'u1')
    
    # Total posts of u1 is 4
    assert result['total_post'].iloc[0] == 4
    
    # The self-forwarding row (u1 -> u1) should be removed
    assert 'u1' not in result['target'].values
    
    # u2 shared 2 posts
    u2_row = result[result['target'] == 'u2']
    assert u2_row['shared_post'].iloc[0] == 2
    assert u2_row['weighted_post'].iloc[0] == 2 / 4

def test_get_follower_followee_network():
    df_network = pd.DataFrame({
        'from_id': ['u1', 'u1', 'u2', 'u2'],
        'forwarder_id': ['u2', 'u3', 'u1', 'u3']
    })
    
    ff_df = get_follower_followee_network(df_network)
    
    assert len(ff_df) == 4 # u1->u2, u1->u3, u2->u1, u2->u3
    assert 'source' in ff_df.columns
    assert 'target' in ff_df.columns
    assert 'shared_post' in ff_df.columns
    assert 'total_post' in ff_df.columns
    assert 'weighted_post' in ff_df.columns
    
    u1_u2_edge = ff_df[(ff_df['source'] == 'u1') & (ff_df['target'] == 'u2')]
    assert len(u1_u2_edge) == 1
    assert u1_u2_edge['total_post'].iloc[0] == 2
    assert u1_u2_edge['shared_post'].iloc[0] == 1
