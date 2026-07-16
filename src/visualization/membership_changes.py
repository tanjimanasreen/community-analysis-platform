import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from matplotlib.lines import Line2D
import ast
import os

from src.themes.membership_changes import calculate_membership_changes


def draw_members_transition_diagram(output_dir: str, paths: list, matched_df):
    if not paths:
        print("No paths to draw membership changes for.")
        return

    all_comm = {}
    count = 1
    for path in paths:
        comm = {}
        for p in path:
            start_matches = matched_df[matched_df.start_month_community == p]
            if not start_matches.empty:
                members_raw = start_matches.start_month_members.values[0]
            else:
                end_matches = matched_df[matched_df.end_month_community == p]
                if not end_matches.empty:
                    members_raw = end_matches.end_month_members.values[0]
                else:
                    members_raw = "[]"

            if isinstance(members_raw, str):
                try:
                    members = ast.literal_eval(members_raw)
                except:
                    members = []
            else:
                members = members_raw

            comm[p] = members

        all_comm[count] = comm
        count += 1

    os.makedirs(output_dir, exist_ok=True)

    for i in range(1, len(all_comm) + 1):
        membership_changes = calculate_membership_changes(all_comm[i])

        fig, axs = plt.subplots(
            1, len(membership_changes), figsize=(10 * len(membership_changes), 10)
        )
        if len(membership_changes) == 1:
            axs = [axs]

        all_members = []
        prev_ax = None

        for ax, (month, data) in zip(axs, membership_changes.items()):
            num_members = len(data["members"])
            if num_members == 0:
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis("off")
                ax.set_title(month, fontsize=14)
                continue

            circle_size = max(0.04, min(0.06, 0.2 / max(1, num_members)))
            grid_size = int(np.ceil(np.sqrt(num_members)))
            spacing = 0.8 / grid_size

            member_positions = {
                member: (
                    0.5 + (idx % grid_size - grid_size // 2) * spacing,
                    0.5 + (idx // grid_size - grid_size // 2) * spacing,
                )
                for idx, member in enumerate(data["members"])
            }

            for member, pos in member_positions.items():
                if member not in data["new_members"]:
                    color = "green"
                else:
                    if member in all_members:
                        color = "grey"
                    else:
                        color = "red"

                member_circle = patches.Circle(
                    pos, circle_size, edgecolor="black", facecolor=color, linewidth=1.5
                )
                ax.add_patch(member_circle)

            all_members += data["members"]

            if prev_ax is not None:
                con = patches.ConnectionPatch(
                    xyA=(1.0, 0.5),
                    xyB=(0.01, 0.5),
                    coordsA="axes fraction",
                    coordsB="axes fraction",
                    axesA=prev_ax,
                    axesB=ax,
                    arrowstyle="simple",
                    linestyle="-",
                    color="black",
                    linewidth=1,
                )
                fig.add_artist(con)

            prev_ax = ax
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.set_title(month, fontsize=14)

        legend_elements = [
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="green",
                markersize=10,
                label="Existing Member",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="red",
                markersize=10,
                label="New Member",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="grey",
                markersize=10,
                label="Reappearing Member",
            ),
        ]
        fig.legend(
            handles=legend_elements,
            loc="upper left",
            fontsize=10,
            title="Member Status",
            bbox_to_anchor=(1.05, 1),
        )

        fig.subplots_adjust(wspace=1)

        filename = f"community_changes_{i}.png"
        save_file_path = os.path.join(output_dir, filename)
        try:
            plt.savefig(save_file_path, dpi=300, transparent=True, bbox_inches="tight")
            print(f"Saved {save_file_path}")
        except Exception as e:
            print(f"Error saving {filename}: {e}")
        finally:
            plt.close(fig)
