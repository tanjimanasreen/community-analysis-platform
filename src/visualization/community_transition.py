import plotly.graph_objects as go
import ast
import os

def draw_community_transition_diagram(output_dir: str, source_ind: list, target_ind: list, score: list, all_community: list, matched_df):
    if not all_community:
        print("No community transitions to draw.")
        return
        
    # Define color palette for nodes
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
        'october': "rgba(197, 176, 213, 0.8)",
        'november': "rgba(23, 190, 207, 0.8)",
        'december': "rgba(158, 218, 229, 0.8)"
    }
    
    # Assign node colors based on their month
    node_colors = [month_colors.get(label.split('_')[0].lower(), "rgba(100, 100, 100, 0.8)") for label in all_community]
    
    # Scale the score into grayscale values for link colors
    max_gray, min_gray = 105, 220
    score_range = max(score) - min(score) if score else 0
    if score_range == 0:
        gray_values = [min_gray] * len(score)
    else:
        gray_values = [int(min_gray + (max_gray - min_gray) * ((s - min(score)) / score_range)) for s in score]
    link_colors = [f"rgba({gray}, {gray}, {gray}, 0.9)" for gray in gray_values]
    
    # Define x positions based on months
    months_order = {
        'january': 0.1, 'february': 0.2, 'march': 0.3, 'april': 0.4,
        'may': 0.5, 'june': 0.6, 'july': 0.7, 'august': 0.8,
        'september': 0.9, 'october': 1.0, 'november': 1.1, 'december': 1.2
    }
    
    node_positions_x = [months_order.get(label.split('_')[0].lower(), 0) for label in all_community]
    node_positions_y = [0.9 - (i / len(all_community)) for i in range(len(all_community))]

    # Community and member labels
    community_and_members = []
    for com in all_community:
        start_matches = matched_df[matched_df.start_month_community == com]
        if not start_matches.empty:
            members_raw = start_matches.start_month_members.to_list()[0]
        else:
            end_matches = matched_df[matched_df.end_month_community == com]
            if not end_matches.empty:
                members_raw = end_matches.end_month_members.to_list()[0]
            else:
                members_raw = "[]"
                
        if isinstance(members_raw, str):
            try:
                members = ast.literal_eval(members_raw)
            except:
                members = []
        else:
            members = members_raw
            
        community_and_members.append(f"{com}<br>Members: {len(members)}")

    # Create the Sankey diagram
    sankey = go.Sankey(
        valueformat=".1f",
        node=dict(
            pad=15,
            thickness=30,
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

    # Combine Sankey trace
    fig = go.Figure(data=[sankey])
    
    fig.update_layout(
        font_size=12,
        width=1000,
        height=800,
        plot_bgcolor="rgba(0,0,0,0)",
        title_text="Community Transitions"
    )

    fig.update_xaxes(showgrid=False, visible=False)
    fig.update_yaxes(showgrid=False, visible=False)
    
    # Save the figure as an image and HTML file
    os.makedirs(output_dir, exist_ok=True)
    html_file = os.path.join(output_dir, "community_transition.html")
    fig.write_html(html_file)
    print(f"Saved Sankey diagram to {html_file}")
    
    try:
        png_file = os.path.join(output_dir, "community_transition.png")
        fig.write_image(png_file)
        print(f"Saved Sankey PNG to {png_file}")
    except Exception as e:
        print(f"Skipping PNG export (requires kaleido): {e}")
