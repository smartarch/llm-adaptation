import pandas as pd
import matplotlib.pyplot as plt
import sys


def area_drone_state(df: pd.DataFrame, ax=None):
    area_cols = ['CHARGING', 'MOVING_TO_CHARGER', 'PROTECTING',  'MOVING_TO_FIELD', 'IDLE', 'TERMINATED']
    colors = ['green', 'lightgreen', 'blue', 'lightblue', 'lightgray', 'black']
    df[area_cols].plot.area(ax=ax, color=colors)
    ax.set_ylabel('State Count')
    ax.set_title('Drone States')
    ax.legend(loc='upper right')
    

def area_field_protecting_drones(df: pd.DataFrame, ax=None):
    field_cols = []
    for i in range(1, 10):
        col_name = f'Field_{i}_protecting_drones'
        if col_name not in df.columns:
            break
        field_cols.append(col_name)
        field_cols.append(f'Field_{i}_arriving_drones')
    field_cols.append('IDLE')
    
    colors = list(plt.get_cmap("tab20")(range(len(field_cols) - 1))) + ['lightgray']
    df[field_cols].plot.area(ax=ax, color=colors)
    ax.set_ylabel('Protecting Drones Count')
    ax.set_title('Protecting Drones per Field')
    ax.legend(loc='upper right')


def line_field_protecting_drones(df, ax, relative=True):
    # df['Charging_Sum'] = df['CHARGING'] + df['MOVING_TO_CHARGER']
    # df['Protecting_Sum'] = df['PROTECTING'] + df['MOVING_TO_FIELD']
    # ax.plot(df['step'], df['Charging_Sum'], label='Charging + Moving to Charger', color='green')
    # ax.plot(df['step'], df['Protecting_Sum'], label='Protecting + Moving to Field', color='blue')
    colormap = plt.get_cmap("tab20")
    for i in range(1, 10):
        if f'Field_{i}_protecting_drones' not in df.columns:
            break
        protecting = df[f'Field_{i}_protecting_drones']
        arriving = df[f'Field_{i}_arriving_drones']
        if relative:
            protecting /= df[f'Field_{i}_drones_for_full_protection'] + protecting
            arriving /= df[f'Field_{i}_drones_for_full_protection'] + protecting
        ax.plot(df['step'], protecting, label=f'Protecting Field {i}', color=colormap(2 * (i - 1)))
        ax.plot(df['step'], arriving, label=f'Moving to Field {i}', linestyle='dotted', color=colormap(2 * (i - 1) + 1))
    ax.set_ylabel('Drones' if not relative else 'Protection coverage')
    ax.set_title('Protecting drones')
    ax.legend(loc='upper right')
    
    
def line_threat_level(df, ax):
    threat_cols = [col for col in df.columns if col.endswith('_threat_level')]
    df[threat_cols].plot.line(ax=ax)
    ax.set_ylabel('Threat Level')
    ax.set_title('Threat Levels Over Time')
    ax.legend(loc='upper right')
    ax.set_xlabel('Step')


def line_damage(df, ax):
    df['damage_diff'] = df['damage'].diff().fillna(0)  # fill NaN with 0 for the first step
    ax2 = ax.twinx()  # Create a secondary axis
    ax2.bar(df['step'], df['damage_diff'], label='Damage Difference', color='pink')
    ax2.set_ylim((0, 10))
    ax2.set_zorder(-1)
    ax.plot(df['step'], df['damage'], label='Damage', color='red')
    for i in range(1, 10):
        if f'Field_{i}_damage' not in df.columns:
            break
        ax.plot(df['step'], df[f'Field_{i}_damage'], label=f'Field {i} Damage')
    ax.set_frame_on(False)
    ax.set_xlabel('Step')
    ax.set_ylabel('Damage')
    ax2.set_ylabel('Damage per time step')
    ax.set_title('Damage Over Time')
    ax.legend(loc='upper left')


def draw_plots(file_name: str, show=False):

    # Load the CSV file
    df = pd.read_csv(file_name if file_name.endswith(".csv") else file_name + ".csv")

    # Set up the figure and axes for 3 subplots (stacked vertically)
    fig, axes = plt.subplots(4, 1, figsize=(10, 15), sharex=True)

    area_drone_state(df, axes[0])
    # area_field_protecting_drones(df, axes[0])
    line_field_protecting_drones(df, axes[1])
    line_threat_level(df, axes[2])
    line_damage(df, axes[3])
    

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
