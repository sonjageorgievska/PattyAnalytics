import logging
from patty.conversions import loadLas, writeLas

from nose.tools import SkipTest, assert_greater
import unittest

logging.basicConfig(level=logging.INFO)


class TestVoxelFilter(unittest.TestCase):

    def testFilter162(self):
        '''
        Test Voxel Grid Filter functionality
        '''
        fileLas = 'data/footprints/162.las'
        fileLasOut = 'data/footprints/162_sparse.las'

        # Load point cloud
        pc = loadLas(fileLas)
        # Build Voxel Grid Filter
        vgf = pc.make_voxel_grid_filter()

        # Filter with Voxel size 1
        vgf.set_leaf_size(1, 1, 1)
        pc2 = vgf.filter()

        # Filter with Voxel size 0.1
        vgf.set_leaf_size(0.1, 0.1, 0.1)
        pc3 = vgf.filter()

        # Filter with Voxel size 10
        vgf.set_leaf_size(10, 10, 10)
        pc4 = vgf.filter()

        assert_greater(len(pc), len(pc2))
        assert_greater(len(pc3), len(pc2))
        assert_greater(len(pc), len(pc4))

        pc2.offset = pc.offset
        writeLas(fileLasOut, pc2)

        logging.info(
            'Voxel grid filter has been applied to point cloud (making it sparse). You can view the results using CloudCompare.')
        logging.info('  Original point cloud: ' + fileLas)
        logging.info('  Sparse point cloud  : ' + fileLasOut)
