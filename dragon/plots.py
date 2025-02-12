import pandas as pd
import matplotlib.pyplot as plt
import sys


def draw_plots(file_name: str, show=False):

    # Load the CSV file
    df = pd.read_csv(file_name if file_name.endswith(".csv") else file_name + ".csv")

    # Set up the figure and axes for 3 subplots (stacked vertically)
    fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True)

    # Area Chart of Villager counts and locations
    area_cols = ['farmers_village', 'warriors_village', 'farmers_cave',  'warriors_cave']
    colors = ['green', 'lightgreen', 'blue', 'lightblue']
    df[area_cols].plot.area(ax=axes[0], color=colors)
    axes[0].set_ylabel('Villager Count')
    axes[0].set_title('Villager Locations')
    axes[0].legend(loc='upper right')

    # Line Chart of Dragon HP
    df['hp_diff'] = -df['dragon_hp'].diff().fillna(0)  # fill NaN with 0 for the first step
    ax2 = axes[2].twinx()  # Create a secondary axis
    ax2.bar(df['step'], df['hp_diff'], label='Damage dealt', color='pink')
    # ax2.set_ylim((0, 10))
    ax2.set_zorder(-1)
    axes[2].plot(df['step'], df['dragon_hp'], label='Dragon HP', color='red')
    axes[2].set_frame_on(False)
    axes[2].set_xlabel('Step')
    axes[2].set_ylabel('HP')
    axes[2].set_ylim((0, df['dragon_hp'].max()))
    ax2.set_ylabel('Damage per time step')
    axes[2].set_title('HP Over Time')
    axes[2].legend(loc='upper left')

    # Show the plot
    plt.suptitle(file_name)
    plt.tight_layout()
    plt.savefig(file_name + ".png")
    if show:
        plt.show()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        file_name = sys.argv[1]
    else:
        # file_name = "logs/2024-10-04-15-23-15-fake"
        file_name = input("Enter file name: ")

    draw_plots(file_name, show=True)
