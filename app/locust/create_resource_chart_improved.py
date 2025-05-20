import matplotlib.pyplot as plt
import numpy as np

# Create sample data based on test scenarios
scenarios = ['Baseline', 'Moderate Load', 'Heavy Load', 'Spike Test', 'Endurance Test']
cpu_values = [25, 45, 78, 92, 40]  # Estimated CPU percentage
memory_values = [40, 55, 72, 85, 50]  # Estimated Memory percentage

# Create side-by-side bar chart
fig, ax1 = plt.subplots(figsize=(10, 6))

x = np.arange(len(scenarios))
width = 0.35

# CPU usage on primary y-axis
bars1 = ax1.bar(x - width/2, cpu_values, width, label='CPU Usage (%)', color='royalblue')
ax1.set_ylabel('CPU Usage (%)')
ax1.set_ylim(0, 100)

# Memory usage on secondary y-axis
ax2 = ax1.twinx()
bars2 = ax2.bar(x + width/2, memory_values, width, label='Memory Usage (%)', color='seagreen')
ax2.set_ylabel('Memory Usage (%)')
ax2.set_ylim(0, 100)

# Add values on top of bars
for i, v in enumerate(cpu_values):
    ax1.text(i - width/2, v + 2, str(v), ha='center', fontsize=9)

for i, v in enumerate(memory_values):
    ax2.text(i + width/2, v + 2, str(v), ha='center', fontsize=9)

ax1.set_title('Estimated Resource Usage by Test Scenario', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(scenarios, rotation=45, ha='right')

# Add scaling threshold line
ax1.axhline(y=80, linestyle='--', color='red', alpha=0.7, label='Scaling Threshold (80%)')

# Add legends
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')

# Add annotations
ax1.annotate('HPA triggered', xy=(3, 92), xytext=(3.3, 85),
            arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8))

# Add grid for better readability
ax1.grid(axis='y', linestyle='--', alpha=0.3)

plt.figtext(0.5, 0.01, 'Note: This chart shows estimated resource usage patterns based on typical cloud-native applications under load testing.', 
           ha='center', fontsize=8, style='italic')

plt.tight_layout()
plt.savefig('results_20250520_165746/report/resource_usage_comparison.png', dpi=120)
print('Improved chart saved successfully!')
