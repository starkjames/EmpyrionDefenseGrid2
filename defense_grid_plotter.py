import streamlit as st
import numpy as np
import plotly.graph_objects as go
import math

# --- Page Setup ---
st.set_page_config(page_title="Empyrion Orbital Defense Planner", layout="wide")
st.markdown("""<h1 style='margin-top: -60px; margin-bottom: -20px;'>🛰️ Orbital Defense Grid Planner</h1><p style='margin-bottom: -10px;'>Use this tool to plan and visualize <a href="https://steamcommunity.com/sharedfiles/filedetails/?id=1269752162">turret</a> coverage for a space base in <strong>Empyrion: Galactic Survival</strong>.</p>""", unsafe_allow_html=True)

# --- Known Turret Types ---
turret_options = {
    "Minigun Turret (850m)": 850,
    "Cannon Turret (925m)": 925,
    "Pulse Laser Turret (1.09km)": 1090,
    "Artillery Turret (1.10km)": 1100,
    "Flak Turret (1.14km)": 1140,
    "Rocket Turret (1.15km)": 1150,
    "Plasma Turret (1.20km)": 1200
}

# --- Sidebar Description & Inputs ---
st.sidebar.header("🛠️ Base & Defense Parameters")
center_x = st.sidebar.number_input("Base X coordinate", value=0)
center_y = st.sidebar.number_input("Base Y coordinate", value=0)
center_z = st.sidebar.number_input("Base Z coordinate", value=0)
base_diameter = st.sidebar.number_input("Base Diameter", value=300)
base_radius = base_diameter / 2
defense_diameter = st.sidebar.slider("Defense Perimeter Diameter", min_value=200, max_value=12000, value=4500, step=100)
defense_radius = defense_diameter / 2
turret_type = st.sidebar.selectbox("Turret Type", list(turret_options.keys()))
turret_range = turret_options[turret_type]
range_display_mode = st.sidebar.selectbox(
    "Firing Range Display Mode",
    options=["Off", "Spheres", "Flat Projection"],
    index=0
)
density_factor = st.sidebar.number_input("Turret Density Factor", min_value=1.0, max_value=3.0, value=1.75, step=0.05)

# --- Core Computation ---
def generate_fibonacci_sphere_points(n, radius, center):
    points = []
    phi = math.pi * (3. - math.sqrt(5.))  # golden angle
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2
        radius_proj = math.sqrt(1 - y * y)
        theta = phi * i
        x = math.cos(theta) * radius_proj
        z = math.sin(theta) * radius_proj
        points.append((
            round(center[0] + x * radius),
            round(center[1] + y * radius),
            round(center[2] + z * radius)
        ))
    return np.array(points)

sphere_surface_area = 4 * math.pi * defense_radius**2
turret_coverage_area = math.pi * turret_range**2
estimated_turrets = math.ceil(density_factor * sphere_surface_area / turret_coverage_area)
turret_positions = generate_fibonacci_sphere_points(estimated_turrets, defense_radius, (center_x, center_y, center_z))

# --- 3D Plot ---
fig = go.Figure()

# Base sphere
u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
x = center_x + base_radius * np.cos(u) * np.sin(v)
y = center_y + base_radius * np.sin(u) * np.sin(v)
z = center_z + base_radius * np.cos(v)
fig.add_trace(go.Surface(x=x, y=y, z=z, opacity=1, showscale=False, colorscale=[[0, 'blue'], [1, 'blue']], hoverinfo='skip'))

# Defense perimeter wireframe
x2 = center_x + defense_radius * np.cos(u) * np.sin(v)
y2 = center_y + defense_radius * np.sin(u) * np.sin(v)
z2 = center_z + defense_radius * np.cos(v)
fig.add_trace(go.Surface(x=x2, y=y2, z=z2, opacity=0.05, showscale=False, colorscale=[[0, 'gray'], [1, 'gray']], hoverinfo='skip'))

# Turret markers
fig.add_trace(go.Scatter3d(
    x=turret_positions[:,0], y=turret_positions[:,1], z=turret_positions[:,2],
    mode='markers', marker=dict(size=4, color='red'), name='Turrets'))

# Firing range spheres
if range_display_mode == "Spheres":
    for tx, ty, tz in turret_positions:
        ur, vr = np.mgrid[0:2*np.pi:10j, 0:np.pi:10j]
        xr = tx + turret_range * np.cos(ur) * np.sin(vr)
        yr = ty + turret_range * np.sin(ur) * np.sin(vr)
        zr = tz + turret_range * np.cos(vr)

        # Transparent volume
        fig.add_trace(go.Surface(
            x=xr, y=yr, z=zr, opacity=0.02, showscale=False,
            colorscale=[[0, 'red'], [1, 'red']], hoverinfo='skip'
        ))

        # Grid overlay
        fig.add_trace(go.Surface(
            x=xr, y=yr, z=zr,
            opacity=0.15,
            surfacecolor=np.zeros_like(xr),
            showscale=False,
            colorscale=[[0, 'darkred'], [1, 'darkred']],
            hoverinfo='skip'
        ))


# Flat projection mode
elif range_display_mode == "Flat Projection":
    for tx, ty, tz in turret_positions:
        turret_vec = np.array([tx - center_x, ty - center_y, tz - center_z])
        turret_unit = turret_vec / np.linalg.norm(turret_vec)

        angle_range = turret_range / defense_radius
        if angle_range >= 1.0:
            angle_range = 0.999  # clamp to valid acos range

        angle = math.acos(1 - (angle_range**2) / 2)  # central angle subtended
        steps = 36
        theta = np.linspace(0, 2 * np.pi, steps)
        circle_pts = []

        # Create orthogonal basis
        if turret_unit[0] != 0 or turret_unit[1] != 0:
            ref = np.array([0, 0, 1])
        else:
            ref = np.array([0, 1, 0])

        u = np.cross(turret_unit, ref)
        u /= np.linalg.norm(u)
        v = np.cross(turret_unit, u)
        v /= np.linalg.norm(v)

        for t in theta:
            pt_dir = (np.cos(t) * u + np.sin(t) * v) * math.sin(angle) + turret_unit * math.cos(angle)
            pt = np.array([center_x, center_y, center_z]) + pt_dir * defense_radius
            circle_pts.append(pt)

        circle_pts = np.array(circle_pts)

        # Triangulate the circle with center fan
        center_pt = np.mean(circle_pts, axis=0)
        xs, ys, zs = [], [], []

        for i in range(len(circle_pts)):
            a = circle_pts[i]
            b = circle_pts[(i + 1) % len(circle_pts)]
            xs += [center_pt[0], a[0], b[0]]
            ys += [center_pt[1], a[1], b[1]]
            zs += [center_pt[2], a[2], b[2]]

        fig.add_trace(go.Mesh3d(
            x=xs, y=ys, z=zs,
            color='orange',
            opacity=0.25,
            hoverinfo='skip',
            showscale=False,
            name='Flat Range Fill'
        ))

        fig.add_trace(go.Scatter3d(
            x=np.append(circle_pts[:, 0], circle_pts[0, 0]),
            y=np.append(circle_pts[:, 1], circle_pts[0, 1]),
            z=np.append(circle_pts[:, 2], circle_pts[0, 2]),
            mode='lines',
            line=dict(color='orange', width=2),
            hoverinfo='skip',
            name='Flat Range Outline'
        ))

fig.update_layout(
    margin=dict(l=0, r=0, b=0, t=10),
    scene=dict(
        xaxis_title='X',
        yaxis_title='Y',
        zaxis_title='Z',
        aspectmode='data'
    ),
    height=700,
    showlegend=False
)


# --- Show Plot ---
st.plotly_chart(fig, use_container_width=True)

# --- Output Summary Below Plot ---
st.subheader("📡 Turret Deployment Summary")
st.markdown(f"**Base Diameter:** `{base_diameter}`")
st.markdown(f"**Selected Turret:** {turret_type} — Range: `{turret_range}` units")
st.markdown(f"**Defense Diameter:** `{defense_diameter}` — Estimated Turrets Needed: `{estimated_turrets}`")
st.markdown(f"**Density Factor:** `{density_factor}` — (Higher values eliminate coverage gaps)")

with st.expander("📋 Show Turret Coordinates"):
    for i, (x, y, z) in enumerate(turret_positions, start=1):
        st.text(f"{i:3d}: ({x}, {y}, {z})")
