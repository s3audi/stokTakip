from collections import defaultdict
from pathlib import Path
import sqlite3

import streamlit as st
import altair as alt
import pandas as pd


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="Inventory tracker",
    page_icon=":shopping_bags:",  # This is an emoji shortcode. Could be a URL too.
)


# -----------------------------------------------------------------------------
# Declare some useful functions.


def connect_db():
    """Connects to the sqlite database."""

    DB_FILENAME = Path(__file__).parent / "inventory.db"
    db_already_exists = DB_FILENAME.exists()

    conn = sqlite3.connect(DB_FILENAME)
    db_was_just_created = not db_already_exists

    return conn, db_was_just_created


def initialize_data(conn):
    """Initializes the inventory table with some data."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            units_sold INTEGER,
            units_left INTEGER,
            cost_price REAL,
            reorder_point INTEGER,
            description TEXT
        )
        """
    )

    cursor.execute(
        """
        INSERT INTO inventory
            (item_name, price, units_sold, units_left, cost_price, reorder_point, description)
        VALUES
            -- İçecekler
            ('Şişe Su (500ml)', 1.50, 115, 15, 0.80, 16, 'Susuzluğu gideren şişe su'),
            ('Kola (355ml)', 2.00, 93, 8, 1.20, 10, 'Gazlı içecek'),
            ('Enerji İçeceği (250ml)', 2.50, 12, 18, 1.50, 8, 'Yüksek kafeinli enerji içeceği'),
            ('Kahve (sıcak, büyük)', 2.75, 11, 14, 1.80, 5, 'Taze demlenmiş sıcak kahve'),
            ('Meyve Suyu (200ml)', 2.25, 11, 9, 1.30, 5, 'Meyve suyu karışımı'),

            -- Atıştırmalıklar
            ('Patates Cipsi (küçük)', 2.00, 34, 16, 1.00, 10, 'Tuzlu ve çıtır patates cipsi'),
            ('Çikolata Barı', 1.50, 6, 19, 0.80, 15, 'Çikolatalı ve şekerli bar'),
            ('Granola Bar', 2.25, 3, 12, 1.30, 8, 'Sağlıklı ve besleyici granola bar'),
            ('Kurabiye (6\'lı paket)', 2.50, 8, 8, 1.50, 5, 'Yumuşak ve çiğnenebilir kurabiye'),
            ('Meyveli Atıştırmalık Paket', 1.75, 5, 10, 1.00, 8, 'Kuru meyve ve kuruyemiş karışımı'),

            -- Kişisel Bakım
            ('Diş Macunu', 3.50, 1, 9, 2.00, 5, 'Naneli diş macunu'),
            ('El Dezenfektanı (küçük)', 2.00, 2, 13, 1.20, 8, 'Küçük boy taşınabilir dezenfektan'),
            ('Ağrı Kesici (paket)', 5.00, 1, 5, 3.00, 3, 'Reçetesiz ağrı kesici ilaç'),
            ('Yara Bandı (kutu)', 3.00, 0, 10, 2.00, 5, 'Küçük kesikler için yara bandı kutusu'),
            ('Güneş Kremi (küçük)', 5.50, 6, 5, 3.50, 3, 'Küçük boy güneş koruyucu krem'),

            -- Ev Ürünleri
            ('Pil (AA, 4\'lü paket)', 4.00, 1, 5, 2.50, 3, '4\'lü AA pil paketi'),
            ('Ampul (LED, 2\'li paket)', 6.00, 3, 3, 4.00, 2, 'Enerji tasarruflu LED ampul'),
            ('Çöp Poşeti (küçük, 10\'lu)', 3.00, 5, 10, 2.00, 5, 'Günlük kullanım için küçük çöp poşeti'),
            ('Kağıt Havlu (tek rulo)', 2.50, 3, 8, 1.50, 5, 'Tek rulo kağıt havlu'),
            ('Çok Amaçlı Temizleyici', 4.50, 2, 5, 3.00, 3, 'Çok amaçlı temizlik spreyi'),

            -- Diğerleri
            ('Piyango Bileti', 2.00, 17, 20, 1.50, 10, 'Çeşitli piyango biletleri'),
            ('Gazete', 1.50, 22, 20, 1.00, 5, 'Günlük gazete')
        """
    )
    conn.commit()


def load_data(conn):
    """Loads the inventory data from the database."""
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM inventory")
        data = cursor.fetchall()
    except:
        return None

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "item_name",
            "price",
            "units_sold",
            "units_left",
            "cost_price",
            "reorder_point",
            "description",
        ],
    )

    return df


def update_data(conn, df, changes):
    """Updates the inventory data in the database."""
    cursor = conn.cursor()

    if changes["edited_rows"]:
        deltas = st.session_state.inventory_table["edited_rows"]
        rows = []

        for i, delta in deltas.items():
            row_dict = df.iloc[i].to_dict()
            row_dict.update(delta)
            rows.append(row_dict)

        cursor.executemany(
            """
            UPDATE inventory
            SET
                item_name = :item_name,
                price = :price,
                units_sold = :units_sold,
                units_left = :units_left,
                cost_price = :cost_price,
                reorder_point = :reorder_point,
                description = :description
            WHERE id = :id
            """,
            rows,
        )

    if changes["added_rows"]:
        cursor.executemany(
            """
            INSERT INTO inventory
                (id, item_name, price, units_sold, units_left, cost_price, reorder_point, description)
            VALUES
                (:id, :item_name, :price, :units_sold, :units_left, :cost_price, :reorder_point, :description)
            """,
            (defaultdict(lambda: None, row) for row in changes["added_rows"]),
        )

    if changes["deleted_rows"]:
        cursor.executemany(
            "DELETE FROM inventory WHERE id = :id",
            ({"id": int(df.loc[i, "id"])} for i in changes["deleted_rows"]),
        )

    conn.commit()


# -----------------------------------------------------------------------------
# Draw the actual page, starting with the inventory table.

# Set the title that appears at the top of the page.
"""
# :shopping_bags: Inventory tracker

**Welcome to Alice's Corner Store's intentory tracker!**
This page reads and writes directly from/to our inventory database.
"""

st.info(
    """
    Use the table below to add, remove, and edit items.
    And don't forget to commit your changes when you're done.
    """
)

# Connect to database and create table if needed
conn, db_was_just_created = connect_db()

# Initialize data.
if db_was_just_created:
    initialize_data(conn)
    st.toast("Database initialized with some sample data.")

# Load data from database
df = load_data(conn)

# Display data with editable table
edited_df = st.data_editor(
    df,
    disabled=["id"],  # Don't allow editing the 'id' column.
    num_rows="dynamic",  # Allow appending/deleting rows.
    column_config={
        # Show dollar sign before price columns.
        "price": st.column_config.NumberColumn(format="$%.2f"),
        "cost_price": st.column_config.NumberColumn(format="$%.2f"),
    },
    key="inventory_table",
)

has_uncommitted_changes = any(len(v) for v in st.session_state.inventory_table.values())

st.button(
    "Commit changes",
    type="primary",
    disabled=not has_uncommitted_changes,
    # Update data in database
    on_click=update_data,
    args=(conn, df, st.session_state.inventory_table),
)


# -----------------------------------------------------------------------------
# Now some cool charts

# Add some space
""
""
""

st.subheader("Units left", divider="red")

need_to_reorder = df[df["units_left"] < df["reorder_point"]].loc[:, "item_name"]

if len(need_to_reorder) > 0:
    items = "\n".join(f"* {name}" for name in need_to_reorder)

    st.error(f"We're running dangerously low on the items below:\n {items}")

""
""

st.altair_chart(
    # Layer 1: Bar chart.
    alt.Chart(df)
    .mark_bar(
        orient="horizontal",
    )
    .encode(
        x="units_left",
        y="item_name",
    )
    # Layer 2: Chart showing the reorder point.
    + alt.Chart(df)
    .mark_point(
        shape="diamond",
        filled=True,
        size=50,
        color="salmon",
        opacity=1,
    )
    .encode(
        x="reorder_point",
        y="item_name",
    ),
    use_container_width=True,
)

st.caption("NOTE: The :diamonds: location shows the reorder point.")

""
""
""

# -----------------------------------------------------------------------------

st.subheader("Best sellers", divider="orange")

""
""

st.altair_chart(
    alt.Chart(df)
    .mark_bar(orient="horizontal")
    .encode(
        x="units_sold",
        y=alt.Y("item_name").sort("-x"),
    ),
    use_container_width=True,
)
