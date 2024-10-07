import pandas as pd
import matplotlib.pyplot as plt
import sys


def draw_plots(file_name: str, show=False):

    # Load the CSV file
    df = pd.read_csv(file_name + ".csv")

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
    axes[1].set_ylabel('Sum Count')
    axes[1].set_title('Charging and Protecting drones')
    axes[1].legend(loc='upper right')

    # Line Chart for "damage"
    axes[2].plot(df['step'], df['damage'], label='Damage', color='red')
    axes[2].set_xlabel('Step')
    axes[2].set_ylabel('Damage')
    axes[2].set_title('Damage Over Time')

    # Show the plot
    plt.title(file_name)
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
