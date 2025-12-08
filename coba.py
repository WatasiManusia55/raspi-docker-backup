import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_erd_matplotlib():
    """Membuat ERD menggunakan matplotlib"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(5, 9.5, 'ENTITY RELATIONSHIP DIAGRAM', 
            fontsize=16, fontweight='bold', ha='center')
    ax.text(5, 9, 'Tabel: sensor_data', 
            fontsize=14, ha='center', style='italic')
    
    # Table box
    table_box = patches.Rectangle((1, 1), 8, 6.5, 
                                  linewidth=2, edgecolor='black', 
                                  facecolor='lightblue', alpha=0.3)
    ax.add_patch(table_box)
    
    # Table header
    header_box = patches.Rectangle((1, 6.5), 8, 0.7, 
                                   linewidth=2, edgecolor='black', 
                                   facecolor='green', alpha=0.5)
    ax.add_patch(header_box)
    ax.text(5, 6.85, 'sensor_data', 
            fontsize=14, fontweight='bold', ha='center', color='white')
    
    # Table content
    columns = [
        ("id", "serial (PK)"),
        ("suhu", "double precision"),
        ("kelembaban", "double precision"),
        ("ph", "double precision"),
        ("cahaya", "double precision"),
        ("gas_mq2", "double precision"),
        ("status_mq2", "varchar(50)"),
        ("gas_mq135", "double precision"),
        ("status_mq135", "varchar(50)"),
        ("waktu", "timestamp"),
        ("gas", "double precision")
    ]
    
    y_pos = 6.0
    for i, (col_name, col_type) in enumerate(columns):
        # Alternating row colors
        if i % 2 == 0:
            row_color = 'white'
        else:
            row_color = '#f0f0f0'
        
        row_box = patches.Rectangle((1, y_pos-0.3), 8, 0.5, 
                                    edgecolor='gray', facecolor=row_color)
        ax.add_patch(row_box)
        
        # Column name
        ax.text(1.2, y_pos-0.05, col_name, 
                fontsize=10, fontweight='bold' if i==0 else 'normal')
        
        # Column type
        ax.text(5, y_pos-0.05, col_type, fontsize=10)
        
        # PK indicator
        if i == 0:
            ax.text(8.5, y_pos-0.05, "🔑", fontsize=12)
        
        y_pos -= 0.5
    
    # Legend
    legend_elements = [
        patches.Patch(facecolor='green', alpha=0.5, label='Table Header'),
        patches.Patch(facecolor='lightblue', alpha=0.3, label='Table Body'),
        patches.Patch(facecolor='white', label='Attribute'),
        patches.Patch(facecolor='#f0f0f0', label='Attribute (Alternate)')
    ]
    
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.title('ERD - Sistem Monitoring Sensor', fontsize=18, pad=20)
    plt.tight_layout()
    plt.savefig('erd_sensor_data_matplotlib.png', dpi=300)
    print("✅ ERD berhasil dibuat: erd_sensor_data_matplotlib.png")
    plt.show()

if __name__ == "__main__":
    create_erd_matplotlib()