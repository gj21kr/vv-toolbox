"""Render saved synthetic iliac mesh from two views for local inspection."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'exports/internal-iliac-surface'
data = np.load(folder / 'surface.npz', allow_pickle=False)
v, f = data['vertices_mm'], data['faces']
fig = plt.figure(figsize=(12, 8))
for index, azimuth in enumerate((-65, 25), 1):
    ax = fig.add_subplot(1, 2, index, projection='3d')
    ax.add_collection3d(Poly3DCollection(v[f], facecolors='#c84c58',
                                      linewidths=0, edgecolors='none'))
    lo, hi = v.min(axis=0), v.max(axis=0)
    ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), zlim=(lo[2], hi[2]),
           xlabel='LPS X (mm)', ylabel='LPS Y (mm)', zlabel='LPS Z (mm)',
           title=f'Synthetic iliac junction / azimuth {azimuth}')
    ax.set_box_aspect(hi-lo)
    ax.view_init(elev=15, azim=azimuth)
fig.suptitle('Selected synthetic model; anatomy and mesh collision not validated')
fig.tight_layout()
fig.savefig(folder / 'surface-views.png', dpi=140)
plt.close(fig)
