# This is a sample Python script.
import open3d as o3d
import meshio
from pathlib import Path
import numpy as np
import scipy
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    test = Path(r"C:\Users\Npyle1\dice_working_dir\DICe_examples\2d_plate_with_hole\results\DICe_solution.e")
    test_read = meshio.read(test)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(test_read.points)
    pcd.colors = o3d.utility.DoubleVector(test_read.point_data['VSG_STRAIN_YY'])
    pcd.estimate_normals()
    o3d.visualization.draw_geometries([pcd])

    distances = pcd.compute_nearest_neighbor_distance()
    avg_dist = np.mean(distances)
    radius = 3 * avg_dist
    # run ball-point algorith to create meshes
    bpa_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, o3d.utility.DoubleVector([radius, 5*radius]))
    # poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8, width=0, scale=1.1, linear_fit=True)[0]
    # downsample
    o3d.visualization.draw_geometries([pcd, bpa_mesh])

    o3d.geometry.TetraMesh.create_from_point_cloud(pcd)
    scipy_test = scipy.spatial.Delaunay(pcd.points, qhull_options="QJ")
    tetra = o3d.geometry.TetraMesh()
    tetra.vertices = pcd.points
    tetra.tetras = o3d.utility.Vector4iVector(scipy_test.simplices)
    o3d.visualization.draw_geometries([tetra])
    # dec_mesh = bpa_mesh.simplify_quadric_decimation(100000)
    # # ensures mesh consistency
    # dec_mesh.remove_degenerate_triangles()
    # dec_mesh.remove_duplicated_triangles()
    # dec_mesh.remove_duplicated_vertices()
    # dec_mesh.remove_non_manifold_edges()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

