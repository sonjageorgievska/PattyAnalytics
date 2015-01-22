#!/usr/bin/env python

"""
Run the registration algorithm on PCD or ply files files.
"""

from __future__ import print_function
import argparse
import pcl
import pcl.registration
from pcl.boundaries import estimate_boundaries
import time
import sys
import numpy as np
import conversions
from sklearn.decomposition import PCA

def log(*args, **kwargs):
    print(time.strftime("[%H:%M:%S]"), *args, **kwargs)

def process_args():
    """ Parse arguments from the command-line using argparse """

    # Implemented registration functions
    funcs = {
        'icp': pcl.registration.icp,
        'gicp': pcl.registration.gicp,
        'icp_nl': pcl.registration.icp_nl,
        'ia_ransac': pcl.registration.ia_ransac
    }

    # For use in the argparser to select value from interval
    class Interval(object):
        def __init__(self, minimum, maximum):
            self._min = minimum
            self._max = maximum

        # for the 0.5 in Interval(0, 0.5)
        def __contains__(self, x):
            return self._min < x < self._max

        # make it iterable for pretty printing
        def __iter__(self):
            self._istate = 0
            return self
        def next(self):
            if self._istate == 0:
                self._istate = 1
                return self._min
            elif self._istate == 1:
                self._istate = 2
                return self._max
            else:
                raise StopIteration

    parser = argparse.ArgumentParser(description='Registration for two PLY point clouds')
    parser.add_argument('-f','--function', choices=funcs.keys(), help='Registration algorithm to run. Choose between gicp, icp, icp_nl, and ia_ransac.', default='gicp')
    parser.add_argument('-d','--downsample', metavar="downsample", nargs=1, type=float, help='Downsample to use one point per given voxel size. Suggested value: 0.005.', choices=Interval(0.0, 1.0) )
    parser.add_argument('source', metavar="SOURCE", help="Source LAS file")
    parser.add_argument('target', metavar="TARGET", help="Target LAS file to map source to")
    
    args = parser.parse_args()

    log("reading source", args.source)
    # source = pcl.load(args.source)
    source = conversions.loadLas(args.source)
    log("offset:", source.offset)
    log("reading target ", args.target)
    target = conversions.loadLas(args.target)
    log("offset:", target.offset)
    # target = pcl.load(args.target)
    
    algo = funcs[args.function]
    
    return source, target, algo, args.downsample

def print_output(algo, converged, transf, fitness):
    """ Print some output based on the algorithm output """
    
    log("converged:", converged, "- error:", fitness)
    log("rotation:")
    log("\n", transf[0:3,0:3])
    log("translation:", transf[3, 0:3])
    log("---------------")

def length_3d(pointcloud):
    xyz_array = np.asarray(pointcloud)
    return xyz_array.max(axis=0) - xyz_array.min(axis=0)

def scale(pointcloud, scale_factor):
    transf = np.identity(4, dtype=float)*scale_factor
    transf[3,3] = 1.0
    return pointcloud.transform(transf)

def downsample(pointcloud, voxel_size=0.01):
    old_len = len(pointcloud)
    pc_filter = source.make_voxel_grid_filter()
    pc_filter.set_leaf_size(voxel_size, voxel_size, voxel_size)
    filtered_pointcloud = pc_filter.filter()
    new_len = len(filtered_pointcloud)
    decrease_percent = (old_len - new_len)*100 / old_len
    log("number of points reduced from", old_len, "to", new_len, "(", decrease_percent, "% decrease)")
    return filtered_pointcloud

def register_scale_offset_from_footprint(footprint, pointcloud):
    ''' Returns a 3d-offset and uniform scale value from footprint.
    The scale is immediately applied to the pointcloud, the offset is set to the patty_registration.conversions.RegisteredPointCloud'''
    fp_min = footprint.min(axis=0)
    fp_max = footprint.max(axis=0)
    fp_center = (fp_min + fp_max) / 2.0

    xyz_array = np.asarray(pointcloud)
    pc_min = xyz_array.min(axis=0)
    pc_max = xyz_array.max(axis=0)
    
    pc_size = pc_max - pc_min
    fp_size = fp_max - fp_min
    
    pc_registration_scale = np.mean(fp_size[0:1]/pc_size[0:1])
    # Take the footprint as the real offset, and correct the z-offset
    # The z-offset of the footprint will be ground level, the z-offset of the
    # pointcloud will include the monuments height

    xyz_array *= pc_registration_scale
    pc_min *= pc_registration_scale
    pc_max *= pc_registration_scale
    
    conversions.register(pointcloud, offset=fp_center - (pc_min + pc_max) / 2.0, precision=pointcloud.precision * pc_registration_scale)
    # print(pc_min)
    # print(pc_max)
    # print(pointcloud.offset)
    # print(fp_center)
    
    return pointcloud.offset, pc_registration_scale

def get_pointcloud_boundaries(pointcloud):
    boundary = estimate_boundaries(pointcloud, angle_threshold=0.1, search_radius=0.02, normal_search_radius=0.02)
    return pointcloud.extract(np.where(boundary)[0])

def principal_axes_rotation(data):
    pca = PCA(n_components=data.shape[1])
    pca.fit(data)
    transform = np.zeros((4,4))
    transform[:3,:3] = np.array(pca.components_)
    transform[3,3] = 1.
    
    return transform

def register_from_footprint(pc, footprint):
    

if __name__ == '__main__':
    source, target, algo, voxel_size = process_args()
    
    # choose the maximum size over all coordinates to determine scale
    # src_maxsize = max(length_3d(source))
    # tgt_maxsize = max(length_3d(target))
    
    # preprocess source and target
    # log("scaling source down by: ", src_maxsize)
    # source = scale(source, 1.0/src_maxsize)
    # log("scaling target down by: ", tgt_maxsize)
    # target = scale(target, 1.0/tgt_maxsize)

    if voxel_size is not None:
        log("downsampling source using voxel size", voxel_size)
        source = downsample(source, voxel_size=voxel_size)
        log("downsampling target using voxel size", voxel_size)
        target = downsample(target, voxel_size=voxel_size)

    log("------", algo.__name__, "-----")
    converged, transf, estimate, fitness = algo(source, target)
    print_output(algo, converged, transf, fitness)