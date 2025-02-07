import pandas as pd
import matplotlib.pyplot as plt
import sys


def draw_plots(file_name: str, show=False):

    # Load the CSV file
    df = pd.read_csv(file_name if file_name.endswith(".csv") else file_name + ".csv")

    # Set up the figure and axes for 3 subplots (stacked vertically)
    fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=True)

    # Area Chart of drone state
    area_cols = ['CHARGING', 'MOVING_TO_CHARGER', 'PROTECTING',  'MOVING_TO_FIELD', 'IDLE', 'TERMINATED']
    colors = ['green', 'lightgreen', 'blue', 'lightblue', 'lightgray', 'black']
    df[area_cols].plot.area(ax=axes[0], color=colors)
    axes[0].set_ylabel('State Count')
    axes[0].set_title('Drone States')
    axes[0].legend(loc='upper right')

    # Line Chart (Sum of CHARGING + MOVING_TO_CHARGER and PROTECTING + MOVING_TO_FIELD)
    df['Charging_Sum'] = df['CHARGING'] + df['MOVING_TO_CHARGER']
    df['Protecting_Sum'] = df['PROTECTING'] + df['MOVING_TO_FIELD']
    axes[1].plot(df['step'], df['Charging_Sum'], label='Charging + Moving to Charger', color='green')
    axes[1].plot(df['step'], df['Protecting_Sum'], label='Protecting + Moving to Field', color='blue')
    for i in range(1, 10):
        if f'Field_{i}_protecting_drones' not in df.columns:
            break
        axes[1].plot(df['step'], df[f'Field_{i}_protecting_drones'], label=f'Protecting Field {i}', linestyle='dotted')
    axes[1].set_ylabel('Sum Count')
    axes[1].set_title('Charging and Protecting drones')
    axes[1].legend(loc='upper right')

    # Line Chart for "damage"
    df['damage_diff'] = df['damage'].diff().fillna(0)  # fill NaN with 0 for the first step
    ax2 = axes[2].twinx()  # Create a secondary axis
    ax2.bar(df['step'], df['damage_diff'], label='Damage Difference', color='pink')
    ax2.set_ylim((0, 10))
    ax2.set_zorder(-1)
    axes[2].plot(df['step'], df['damage'], label='Damage', color='red')
    for i in range(1, 10):
        if f'Field_{i}_damage' not in df.columns:
            break
        axes[2].plot(df['step'], df[f'Field_{i}_damage'], label=f'Field {i} Damage')
    axes[2].set_frame_on(False)
    axes[2].set_xlabel('Step')
    axes[2].set_ylabel('Damage')
    ax2.set_ylabel('Damage per time step')
    axes[2].set_title('Damage Over Time')
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
