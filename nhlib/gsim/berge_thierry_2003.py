# nhlib: A New Hazard Library
# Copyright (C) 2012 GEM Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Module exports :class:`BergeThierry2003`.
"""
from __future__ import division

import numpy as np

from nhlib.gsim.base import GMPE, CoeffsTable
from nhlib import const
from nhlib.imt import PGA, PGV, SA


class BergeThierry2003(GMPE):
    """
    Implements GMPE developed by Berge-Thierry et al.
    and published as "New empirical response spectral attenuation laws for
    moderate European earthquakes" (2003, Journal of Earthquake Engineering,
    Volume 7, No. 2, pages 193-222).
    """
    #: Supported tectonic region type is stable shallow crust.
    #: See paragraph 'Introduction', pag 193.
    DEFINED_FOR_TECTONIC_REGION_TYPE = const.TRT.STABLE_CONTINENTAL

    #: Supported intensity measure type is spectral acceleration.
    #: See table 3, pag 203.
    DEFINED_FOR_INTENSITY_MEASURE_TYPES = set([
        SA
    ])

    #: Supported intensity measure component is both horizontal
    #: :attr:`~nhlib.const.IMC.BOTH_HORIZONTAL`.
    #: See paragraph 'Record selection and data processing', pag 195.
    DEFINED_FOR_INTENSITY_MEASURE_COMPONENT = const.IMC.BOTH_HORIZONTAL

    #: Supported standard deviation type is total.
    #: See paragraph 'Comments on the horizontal motion attenuation
    #: coefficients (5% damping)', pag 202.
    DEFINED_FOR_STANDARD_DEVIATION_TYPES = set([
        const.StdDev.TOTAL
    ])

    #: Required site parameter is vs30 (used to distinguish rock (vs30 >= 800 m/s)
    #: and alluvium (300 m/s < vs30 < 800 m/s)).
    #: See paragraph 'Site classification', pag 201.
    REQUIRES_SITES_PARAMETERS = set(('vs30',))

    #: Required rupture parameter is magnitude.
    #: See equation 1, pag 201.
    REQUIRES_RUPTURE_PARAMETERS = set(('mag',))

    #: Required distance measure is rhypo.
    #: See paragraph 'Distance and magnitude definition', pag 201.
    REQUIRES_DISTANCES = set(('rhypo',))

    def get_mean_and_stddevs(self, sites, rup, dists, imt, stddev_types):
        """
        See :meth:`superclass method
        <nhlib.gsim.base.GroundShakingIntensityModel.get_mean_and_stddevs>`
        for spec of input and result values.
        """
        # extracting dictionary of coefficients specific to required
        # intensity measure type.
        C = {5: self.COEFFS05, 20: self.COEFFS20}[imt[1]][imt]

        # Equation 1, pag 201, with magnitude, distance and site amplification term
        log10_mean = self._compute_magnitude_scaling(rup, C) + \
            self._compute_distance_scaling(rup, C) + \
            self._get_site_amplification(sites, C)
        
        # Convert m/s^2 to g, and take the natural logarithm
        mean = (10**log10_mean) / 981.0
        mean = np.log(mean)

        stddevs = self._get_stddevs(C, stddev_types, num_sites=len(sites.vs30))
        stddevs = np.log(stddevs)

        return mean, stddevs

    def _get_stddevs(self, C, stddev_types, num_sites):
        """
        Return standard deviations as defined in table 3, pag 203.
        """
        stddevs = []
        for stddev_type in stddev_types:
            assert stddev_type in self.DEFINED_FOR_STANDARD_DEVIATION_TYPES
            if stddev_type == const.StdDev.TOTAL:
                stddevs.append(C['std'] + np.zeros(num_sites))
        stddevs = 10**np.array(stddevs)
        return stddevs

    def _compute_magnitude_scaling(self, rup, C):
        """
        Compute magnitude-scaling term, equation 1, pag 201.
        """
        val = C['a'] * rup.mag
        return val

    def _compute_distance_scaling(self, dists, C):
        """
        Compute distance-scaling term, equation 1, pag 201.
        """
        val = C['b'] * dists.rhypo - np.log10(dists.rhypo)
        return val

    def _get_site_amplification(self, sites, C):
        """
        Compute site amplification term, equation 1, pag 201.
        Distinguishes between rock (vs30 >= 800 m/s) and alluvium
        (300 m/s < vs30 <= 800 m/s)).
        See paragraph 'Site classification', pag 201.
        """
        choice_dict = {True: C['c1'], False: C['c2']}
        val = np.array([choice_dict[vs30 >= 800.0] for vs30 in sites.vs30])
        return val


    #: Coefficient table is constructed from values in table 2, pag 203.
    #: Spectral acceleration is defined for damping of 5%.
    #: See paragraph 'Seismic Motion Attenuation Law', pag 201.
    #: a is the magnitude scaling coefficient.
    #: b is the distance scaling coefficient.
    #: c is the site amplification coefficient (c1 for rock (vs30 >= 800 m/s)
    #: and c2 for alluvium (300 m/s < vs30 <= 800 m/s))
    #: std is the total standard deviation.

    # TODO: add other damping factors
    # TODO: check if first period = 3.0000E-02 or 2.9412E-02
    COEFFS05 = CoeffsTable(sa_damping=5, table="""\
    IMT    a    b    c1    c2    std
    2.9412E-02    3.1180E-01    -9.3030E-04 1.5370E+00  1.5730E+00    2.9230E-01
    3.0000E-02    3.1140E-01    -9.3340E-04    1.5410E+00    1.5760E+00    2.9240E-01
    3.2258E-02    3.0970E-01    -9.4220E-04    1.5580E+00    1.5890E+00    2.9280E-01
    3.4000E-02    3.0830E-01    -9.5470E-04    1.5730E+00    1.6020E+00    2.9350E-01
    3.5714E-02    3.0680E-01    -9.8220E-04    1.5930E+00    1.6180E+00    2.9470E-01
    4.0000E-02    3.0330E-01    -1.1190E-03    1.6530E+00    1.6650E+00    2.9820E-01
    4.5455E-02    3.0160E-01    -1.2820E-03    1.7010E+00    1.7000E+00    3.0150E-01
    5.0000E-02    2.9920E-01    -1.3410E-03    1.7400E+00    1.7290E+00    3.0090E-01
    5.3000E-02    2.9810E-01    -1.4290E-03    1.7660E+00    1.7490E+00    3.0220E-01
    5.5556E-02    2.9690E-01    -1.4320E-03    1.7850E+00    1.7650E+00    3.0270E-01
    5.8824E-02    2.9600E-01    -1.4600E-03    1.8090E+00    1.7840E+00    3.0400E-01
    5.9999E-02    2.9600E-01    -1.4720E-03    1.8140E+00    1.7880E+00    3.0410E-01
    6.2500E-02    2.9650E-01    -1.5070E-03    1.8260E+00    1.7960E+00    3.0470E-01
    6.4998E-02    2.9440E-01    -1.5150E-03    1.8510E+00    1.8170E+00    3.0590E-01
    6.6667E-02    2.9330E-01    -1.5130E-03    1.8650E+00    1.8290E+00    3.0590E-01
    6.8966E-02    2.9240E-01    -1.5460E-03    1.8810E+00    1.8420E+00    3.0480E-01
    6.9999E-02    2.9200E-01    -1.5700E-03    1.8880E+00    1.8490E+00    3.0460E-01
    7.1429E-02    2.9090E-01    -1.5830E-03    1.9010E+00    1.8610E+00    3.0470E-01
    7.4074E-02    2.8790E-01    -1.5550E-03    1.9260E+00    1.8870E+00    3.0590E-01
    7.5002E-02    2.8710E-01    -1.5400E-03    1.9330E+00    1.8930E+00    3.0660E-01
    7.6923E-02    2.8570E-01    -1.5200E-03    1.9470E+00    1.9060E+00    3.0720E-01
    8.0000E-02    2.8660E-01    -1.5310E-03    1.9540E+00    1.9110E+00    3.0610E-01
    8.3333E-02    2.8580E-01    -1.5520E-03    1.9680E+00    1.9270E+00    3.0580E-01
    8.4998E-02    2.8560E-01    -1.5830E-03    1.9760E+00    1.9350E+00    3.0530E-01
    8.6957E-02    2.8480E-01    -1.5710E-03    1.9870E+00    1.9460E+00    3.0420E-01
    9.0001E-02    2.8190E-01    -1.5360E-03    2.0110E+00    1.9730E+00    3.0200E-01
    9.0909E-02    2.8090E-01    -1.5280E-03    2.0200E+00    1.9810E+00    3.0160E-01
    9.5238E-02    2.7810E-01    -1.5430E-03    2.0540E+00    2.0100E+00    3.0170E-01
    1.0000E-01    2.7860E-01    -1.4740E-03    2.0590E+00    2.0160E+00    3.0190E-01
    1.0526E-01    2.7760E-01    -1.4220E-03    2.0720E+00    2.0340E+00    3.0430E-01
    1.1000E-01    2.7830E-01    -1.4420E-03    2.0750E+00    2.0450E+00    3.0730E-01
    1.1111E-01    2.7830E-01    -1.4380E-03    2.0770E+00    2.0470E+00    3.0790E-01
    1.1765E-01    2.7930E-01    -1.4380E-03    2.0810E+00    2.0560E+00    3.1030E-01
    1.2000E-01    2.8060E-01    -1.4360E-03    2.0760E+00    2.0540E+00    3.1060E-01
    1.2500E-01    2.8310E-01    -1.4150E-03    2.0660E+00    2.0510E+00    3.1210E-01
    1.2903E-01    2.8630E-01    -1.4400E-03    2.0520E+00    2.0420E+00    3.1370E-01
    1.3001E-01    2.8670E-01    -1.4250E-03    2.0500E+00    2.0400E+00    3.1420E-01
    1.3333E-01    2.8870E-01    -1.3970E-03    2.0400E+00    2.0330E+00    3.1560E-01
    1.3793E-01    2.9030E-01    -1.3380E-03    2.0320E+00    2.0280E+00    3.1610E-01
    1.4000E-01    2.9150E-01    -1.3220E-03    2.0270E+00    2.0220E+00    3.1660E-01
    1.4286E-01    2.9330E-01    -1.3070E-03    2.0180E+00    2.0140E+00    3.1730E-01
    1.4815E-01    2.9500E-01    -1.2560E-03    2.0090E+00    2.0100E+00    3.1910E-01
    1.4999E-01    2.9550E-01    -1.2180E-03    2.0040E+00    2.0090E+00    3.1960E-01
    1.5385E-01    2.9550E-01    -1.0520E-03    1.9970E+00    2.0070E+00    3.2010E-01
    1.6000E-01    2.9390E-01    -8.0560E-04    1.9960E+00    2.0130E+00    3.2000E-01
    1.6667E-01    2.9520E-01    -7.0970E-04    1.9890E+00    2.0060E+00    3.2150E-01
    1.7001E-01    2.9740E-01    -6.9860E-04    1.9780E+00    1.9940E+00    3.2300E-01
    1.7391E-01    3.0160E-01    -7.3410E-04    1.9570E+00    1.9700E+00    3.2470E-01
    1.7999E-01    3.0890E-01    -7.7930E-04    1.9150E+00    1.9300E+00    3.2670E-01
    1.8182E-01    3.1090E-01    -7.8260E-04    1.9010E+00    1.9190E+00    3.2710E-01
    1.9001E-01    3.1470E-01    -7.3690E-04    1.8680E+00    1.8940E+00    3.2620E-01
    1.9048E-01    3.1490E-01    -7.3370E-04    1.8670E+00    1.8930E+00    3.2620E-01
    2.0000E-01    3.1670E-01    -6.8890E-04    1.8430E+00    1.8810E+00    3.2500E-01
    2.0833E-01    3.1960E-01    -6.7190E-04    1.8140E+00    1.8610E+00    3.2610E-01
    2.1739E-01    3.2540E-01    -6.7500E-04    1.7700E+00    1.8250E+00    3.2810E-01
    2.1978E-01    3.2710E-01    -6.9180E-04    1.7580E+00    1.8150E+00    3.2920E-01
    2.2727E-01    3.3030E-01    -6.6780E-04    1.7260E+00    1.7920E+00    3.3200E-01
    2.3810E-01    3.3400E-01    -6.1710E-04    1.6830E+00    1.7620E+00    3.3670E-01
    2.3998E-01    3.3440E-01    -5.9880E-04    1.6770E+00    1.7580E+00    3.3710E-01
    2.5000E-01    3.3650E-01    -5.7500E-04    1.6510E+00    1.7360E+00    3.3940E-01
    2.5974E-01    3.4300E-01    -7.0750E-04    1.6090E+00    1.6970E+00    3.4220E-01
    2.6316E-01    3.4420E-01    -7.2000E-04    1.5990E+00    1.6880E+00    3.4290E-01
    2.7778E-01    3.5010E-01    -7.5200E-04    1.5500E+00    1.6450E+00    3.4440E-01
    2.8003E-01    3.5110E-01    -7.5300E-04    1.5420E+00    1.6380E+00    3.4470E-01
    2.9002E-01    3.5550E-01    -7.8360E-04    1.5060E+00    1.6050E+00    3.4580E-01
    3.0003E-01    3.5900E-01    -8.5200E-04    1.4770E+00    1.5810E+00    3.4770E-01
    3.0303E-01    3.6020E-01    -8.7370E-04    1.4660E+00    1.5730E+00    3.4830E-01
    3.1696E-01    3.6710E-01    -9.2720E-04    1.4120E+00    1.5250E+00    3.4910E-01
    3.2000E-01    3.6900E-01    -9.4680E-04    1.3970E+00    1.5120E+00    3.4870E-01
    3.3333E-01    3.7420E-01    -1.0100E-03    1.3520E+00    1.4720E+00    3.4740E-01
    3.4002E-01    3.7520E-01    -1.0060E-03    1.3370E+00    1.4610E+00    3.4690E-01
    3.4483E-01    3.7600E-01    -9.6980E-04    1.3260E+00    1.4520E+00    3.4710E-01
    3.5714E-01    3.8070E-01    -9.1140E-04    1.2860E+00    1.4150E+00    3.4810E-01
    3.5997E-01    3.8220E-01    -9.0390E-04    1.2750E+00    1.4050E+00    3.4840E-01
    3.7037E-01    3.8670E-01    -8.6350E-04    1.2370E+00    1.3720E+00    3.4920E-01
    3.7994E-01    3.9090E-01    -8.0740E-04    1.1990E+00    1.3390E+00    3.5000E-01
    3.8462E-01    3.9310E-01    -7.9550E-04    1.1790E+00    1.3210E+00    3.5070E-01
    4.0000E-01    3.9970E-01    -7.0780E-04    1.1190E+00    1.2670E+00    3.5170E-01
    4.1667E-01    4.0280E-01    -6.6130E-04    1.0780E+00    1.2320E+00    3.5120E-01
    4.1999E-01    4.0340E-01    -6.5130E-04    1.0700E+00    1.2260E+00    3.5130E-01
    4.3478E-01    4.0700E-01    -6.1670E-04    1.0290E+00    1.1910E+00    3.5210E-01
    4.3995E-01    4.0890E-01    -6.1180E-04    1.0110E+00    1.1740E+00    3.5270E-01
    4.5455E-01    4.1480E-01    -5.9310E-04    9.6010E-01    1.1250E+00    3.5470E-01
    4.5998E-01    4.1650E-01    -5.8160E-04    9.4400E-01    1.1090E+00    3.5490E-01
    4.7619E-01    4.2220E-01    -5.4040E-04    8.9310E-01    1.0580E+00    3.5550E-01
    4.8008E-01    4.2390E-01    -5.4840E-04    8.7950E-01    1.0450E+00    3.5560E-01
    5.0000E-01    4.3230E-01    -5.6800E-04    8.1500E-01    9.7970E-01    3.5550E-01
    5.2002E-01    4.3720E-01    -5.3960E-04    7.6420E-01    9.3240E-01    3.5680E-01
    5.2632E-01    4.3790E-01    -5.0500E-04    7.5220E-01    9.2080E-01    3.5700E-01
    5.3996E-01    4.3940E-01    -4.3300E-04    7.2710E-01    8.9590E-01    3.5740E-01
    5.5556E-01    4.4180E-01    -3.6010E-04    6.9410E-01    8.6610E-01    3.5870E-01
    5.5991E-01    4.4250E-01    -3.3800E-04    6.8440E-01    8.5710E-01    3.5920E-01
    5.8005E-01    4.4720E-01    -2.7020E-04    6.3570E-01    8.1170E-01    3.6100E-01
    5.8824E-01    4.4920E-01    -2.5220E-04    6.1570E-01    7.9260E-01    3.6090E-01
    5.9988E-01    4.5160E-01    -2.1750E-04    5.8950E-01    7.6820E-01    3.6030E-01
    6.1996E-01    4.5590E-01    -1.9530E-04    5.4780E-01    7.2820E-01    3.6040E-01
    6.2500E-01    4.5690E-01    -1.9950E-04    5.3830E-01    7.1870E-01    3.6090E-01
    6.4020E-01    4.5960E-01    -1.6660E-04    5.1060E-01    6.9100E-01    3.6250E-01
    6.6007E-01    4.6370E-01    -1.5490E-04    4.7250E-01    6.5200E-01    3.6470E-01
    6.6667E-01    4.6550E-01    -1.5500E-04    4.5730E-01    6.3630E-01    3.6490E-01
    6.7981E-01    4.6880E-01    -1.6680E-04    4.2840E-01    6.0810E-01    3.6550E-01
    6.9979E-01    4.7320E-01    -1.7000E-04    3.8570E-01    5.6760E-01    3.6670E-01
    7.1429E-01    4.7710E-01    -2.0190E-04    3.5480E-01    5.3540E-01    3.6800E-01
    7.5019E-01    4.8470E-01    -3.0090E-04    2.8710E-01    4.6810E-01    3.7000E-01
    7.6923E-01    4.8750E-01    -3.1220E-04    2.5450E-01    4.3800E-01    3.7030E-01
    8.0000E-01    4.9400E-01    -2.5680E-04    1.9060E-01    3.7820E-01    3.7140E-01
    8.3333E-01    5.0100E-01    -1.9320E-04    1.2640E-01    3.1450E-01    3.7460E-01
    8.5034E-01    5.0400E-01    -1.4330E-04    9.6150E-02    2.8420E-01    3.7580E-01
    9.0009E-01    5.0980E-01    3.2820E-05    2.0060E-02    2.1300E-01    3.7470E-01
    9.0909E-01    5.1040E-01    8.3930E-05    8.1950E-03    2.0220E-01    3.7440E-01
    1.0000E+00    5.1990E-01    2.5160E-04    -1.1620E-01    8.2900E-02    3.7370E-01
    1.1001E+00    5.2730E-01    3.9080E-04    -2.1230E-01    -2.9000E-02    3.7940E-01
    1.1111E+00    5.2780E-01    4.0740E-04    -2.2070E-01    -3.8750E-02    3.8040E-01
    1.2005E+00    5.3610E-01    4.4790E-04    -3.1330E-01    -1.3380E-01    3.8380E-01
    1.2500E+00    5.4090E-01    4.8600E-04    -3.6790E-01    -1.8910E-01    3.8770E-01
    1.3004E+00    5.4440E-01    5.3290E-04    -4.1130E-01    -2.3770E-01    3.9200E-01
    1.4006E+00    5.4810E-01    7.6760E-04    -4.8700E-01    -3.1550E-01    3.9350E-01
    1.4286E+00    5.4940E-01    8.2720E-04    -5.0950E-01    -3.3850E-01    3.9410E-01
    1.4993E+00    5.5270E-01    9.1240E-04    -5.6040E-01    -3.9350E-01    3.9320E-01
    1.6000E+00    5.5570E-01    9.8440E-04    -6.1860E-01    -4.5830E-01    3.9190E-01
    1.6667E+00    5.5800E-01    1.0850E-03    -6.5640E-01    -5.0260E-01    3.9190E-01
    1.7986E+00    5.6200E-01    1.2450E-03    -7.2580E-01    -5.8340E-01    3.9420E-01
    2.0000E+00    5.6220E-01    1.3750E-03    -7.9630E-01    -6.6600E-01    4.0300E-01
    2.1978E+00    5.6170E-01    1.6520E-03    -8.6560E-01    -7.3950E-01    4.0550E-01
    2.3981E+00    5.6410E-01    1.8290E-03    -9.4060E-01    -8.1580E-01    4.0930E-01
    2.5000E+00    5.6540E-01    1.9210E-03    -9.7870E-01    -8.5420E-01    4.1100E-01
    2.5974E+00    5.6770E-01    2.0060E-03    -1.0190E+00    -8.9800E-01    4.1300E-01
    2.8011E+00    5.6660E-01    2.2770E-03    -1.0710E+00    -9.4950E-01    4.2020E-01
    3.0030E+00    5.6830E-01    2.4490E-03    -1.1300E+00    -1.0140E+00    4.2550E-01
    3.2051E+00    5.6860E-01    2.5360E-03    -1.1790E+00    -1.0690E+00    4.3010E-01
    3.3333E+00    5.7050E-01    2.5330E-03    -1.2200E+00    -1.1110E+00    4.3290E-01
    3.4014E+00    5.7150E-01    2.5410E-03    -1.2430E+00    -1.1350E+00    4.3400E-01
    3.5971E+00    5.7270E-01    2.5730E-03    -1.3000E+00    -1.1940E+00    4.3590E-01
    3.8023E+00    5.7120E-01    2.6620E-03    -1.3500E+00    -1.2420E+00    4.3650E-01
    4.0000E+00    5.7220E-01    2.7110E-03    -1.4170E+00    -1.3030E+00    4.3440E-01
    4.5045E+00    5.8560E-01    2.4490E-03    -1.6620E+00    -1.5200E+00    4.2780E-01
    5.0000E+00    5.9900E-01    2.1050E-03    -1.8860E+00    -1.7290E+00    4.2330E-01
    5.4945E+00    6.1060E-01    1.9410E-03    -2.0720E+00    -1.9040E+00    4.2600E-01
    5.9880E+00    6.1600E-01    1.8800E-03    -2.2010E+00    -2.0280E+00    4.2840E-01
    6.9930E+00    6.1750E-01    1.7660E-03    -2.3730E+00    -2.1920E+00    4.2990E-01
    8.0000E+00    6.1450E-01    1.7210E-03    -2.4910E+00    -2.3080E+00    4.2840E-01
    9.0090E+00    6.1220E-01    1.6370E-03    -2.5920E+00    -2.4080E+00    4.2360E-01
    1.0000E+01    6.0860E-01    1.5630E-03    -2.6680E+00    -2.4850E+00    4.1830E-01
    """)

    COEFFS20 = CoeffsTable(sa_damping=20, table="""\
    IMT    a    b    c1    c2    std
    1.00E+01    5.93E-01    1.53E-03    -2.59E+00    -2.41E+00    4.06E-01
    9.01E+00    5.93E-01    1.56E-03    -2.49E+00    -2.32E+00    4.07E-01
    8.00E+00    5.93E-01    1.61E-03    -2.38E+00    -2.21E+00    4.09E-01
    6.99E+00    5.92E-01    1.66E-03    -2.25E+00    -2.08E+00    4.08E-01
    5.99E+00    5.87E-01    1.71E-03    -2.07E+00    -1.91E+00    4.06E-01
    5.49E+00    5.83E-01    1.76E-03    -1.96E+00    -1.80E+00    4.05E-01
    5.00E+00    5.78E-01    1.83E-03    -1.83E+00    -1.68E+00    4.04E-01
    4.50E+00    5.72E-01    1.89E-03    -1.68E+00    -1.54E+00    4.05E-01
    4.00E+00    5.65E-01    1.96E-03    -1.52E+00    -1.39E+00    4.04E-01
    3.80E+00    5.63E-01    1.95E-03    -1.47E+00    -1.33E+00    4.04E-01
    3.60E+00    5.61E-01    1.91E-03    -1.40E+00    -1.27E+00    4.02E-01
    3.40E+00    5.58E-01    1.89E-03    -1.34E+00    -1.21E+00    4.01E-01
    3.33E+00    5.57E-01    1.88E-03    -1.32E+00    -1.19E+00    4.00E-01
    3.21E+00    5.56E-01    1.83E-03    -1.28E+00    -1.15E+00    3.99E-01
    3.00E+00    5.54E-01    1.74E-03    -1.22E+00    -1.09E+00    3.95E-01
    2.80E+00    5.54E-01    1.60E-03    -1.17E+00    -1.03E+00    3.92E-01
    2.60E+00    5.54E-01    1.43E-03    -1.11E+00    -9.76E-01    3.89E-01
    2.50E+00    5.54E-01    1.37E-03    -1.09E+00    -9.46E-01    3.87E-01
    2.40E+00    5.53E-01    1.32E-03    -1.05E+00    -9.12E-01    3.87E-01
    2.20E+00    5.50E-01    1.20E-03    -9.76E-01    -8.31E-01    3.85E-01
    2.00E+00    5.48E-01    1.02E-03    -9.00E-01    -7.53E-01    3.84E-01
    1.80E+00    5.46E-01    8.04E-04    -8.12E-01    -6.62E-01    3.82E-01
    1.67E+00    5.43E-01    6.53E-04    -7.45E-01    -5.91E-01    3.80E-01
    1.60E+00    5.40E-01    5.78E-04    -7.03E-01    -5.46E-01    3.79E-01
    1.50E+00    5.36E-01    4.68E-04    -6.38E-01    -4.75E-01    3.79E-01
    1.43E+00    5.32E-01    3.90E-04    -5.87E-01    -4.22E-01    3.79E-01
    1.40E+00    5.31E-01    3.54E-04    -5.66E-01    -3.99E-01    3.78E-01
    1.30E+00    5.25E-01    2.19E-04    -4.85E-01    -3.14E-01    3.76E-01
    1.25E+00    5.22E-01    1.61E-04    -4.42E-01    -2.69E-01    3.75E-01
    1.20E+00    5.18E-01    1.02E-04    -4.00E-01    -2.24E-01    3.73E-01
    1.11E+00    5.13E-01    -3.93E-06    -3.20E-01    -1.40E-01    3.70E-01
    1.10E+00    5.12E-01    -1.06E-05    -3.10E-01    -1.29E-01    3.69E-01
    1.00E+00    5.03E-01    -1.15E-04    -2.04E-01    -1.85E-02    3.66E-01
    9.09E-01    4.93E-01    -2.15E-04    -8.75E-02    9.79E-02    3.63E-01
    9.00E-01    4.92E-01    -2.29E-04    -7.59E-02    1.09E-01    3.63E-01
    8.50E-01    4.87E-01    -3.08E-04    -7.74E-03    1.76E-01    3.62E-01
    8.33E-01    4.84E-01    -3.13E-04    1.85E-02    2.01E-01    3.61E-01
    8.00E-01    4.79E-01    -3.25E-04    7.17E-02    2.52E-01    3.60E-01
    7.69E-01    4.74E-01    -3.49E-04    1.22E-01    3.01E-01    3.59E-01
    7.50E-01    4.71E-01    -3.68E-04    1.55E-01    3.32E-01    3.58E-01
    7.14E-01    4.65E-01    -3.97E-04    2.19E-01    3.95E-01    3.56E-01
    7.00E-01    4.62E-01    -4.05E-04    2.46E-01    4.22E-01    3.55E-01
    6.80E-01    4.58E-01    -4.17E-04    2.84E-01    4.59E-01    3.54E-01
    6.67E-01    4.55E-01    -4.26E-04    3.09E-01    4.84E-01    3.54E-01
    6.60E-01    4.54E-01    -4.31E-04    3.22E-01    4.97E-01    3.53E-01
    6.40E-01    4.50E-01    -4.30E-04    3.61E-01    5.36E-01    3.52E-01
    6.25E-01    4.47E-01    -4.33E-04    3.91E-01    5.65E-01    3.52E-01
    6.20E-01    4.46E-01    -4.35E-04    4.01E-01    5.75E-01    3.51E-01
    6.00E-01    4.42E-01    -4.51E-04    4.41E-01    6.12E-01    3.50E-01
    5.88E-01    4.40E-01    -4.62E-04    4.65E-01    6.35E-01    3.50E-01
    5.80E-01    4.38E-01    -4.70E-04    4.82E-01    6.51E-01    3.49E-01
    5.60E-01    4.34E-01    -5.02E-04    5.25E-01    6.91E-01    3.48E-01
    5.56E-01    4.33E-01    -5.11E-04    5.35E-01    7.00E-01    3.48E-01
    5.40E-01    4.29E-01    -5.32E-04    5.72E-01    7.34E-01    3.47E-01
    5.26E-01    4.26E-01    -5.48E-04    6.04E-01    7.65E-01    3.47E-01
    5.20E-01    4.25E-01    -5.60E-04    6.19E-01    7.78E-01    3.46E-01
    5.00E-01    4.20E-01    -5.88E-04    6.67E-01    8.24E-01    3.45E-01
    4.80E-01    4.15E-01    -6.38E-04    7.15E-01    8.71E-01    3.45E-01
    4.76E-01    4.14E-01    -6.49E-04    7.25E-01    8.80E-01    3.45E-01
    4.60E-01    4.10E-01    -7.04E-04    7.67E-01    9.20E-01    3.44E-01
    4.55E-01    4.08E-01    -7.22E-04    7.81E-01    9.34E-01    3.44E-01
    4.40E-01    4.04E-01    -7.72E-04    8.20E-01    9.71E-01    3.43E-01
    4.35E-01    4.03E-01    -7.89E-04    8.33E-01    9.84E-01    3.43E-01
    4.20E-01    3.99E-01    -8.27E-04    8.72E-01    1.02E+00    3.42E-01
    4.17E-01    3.99E-01    -8.35E-04    8.80E-01    1.03E+00    3.42E-01
    4.00E-01    3.94E-01    -8.68E-04    9.24E-01    1.07E+00    3.41E-01
    3.85E-01    3.90E-01    -8.88E-04    9.66E-01    1.11E+00    3.40E-01
    3.80E-01    3.89E-01    -8.93E-04    9.79E-01    1.12E+00    3.40E-01
    3.70E-01    3.86E-01    -9.03E-04    1.01E+00    1.14E+00    3.39E-01
    3.60E-01    3.83E-01    -9.20E-04    1.04E+00    1.17E+00    3.39E-01
    3.57E-01    3.82E-01    -9.25E-04    1.04E+00    1.18E+00    3.39E-01
    3.45E-01    3.78E-01    -9.44E-04    1.08E+00    1.21E+00    3.38E-01
    3.40E-01    3.77E-01    -9.52E-04    1.09E+00    1.22E+00    3.38E-01
    3.33E-01    3.75E-01    -9.54E-04    1.11E+00    1.24E+00    3.38E-01
    3.20E-01    3.71E-01    -9.48E-04    1.15E+00    1.27E+00    3.37E-01
    3.17E-01    3.70E-01    -9.46E-04    1.16E+00    1.28E+00    3.36E-01
    3.03E-01    3.65E-01    -9.23E-04    1.21E+00    1.32E+00    3.35E-01
    3.00E-01    3.64E-01    -9.16E-04    1.22E+00    1.33E+00    3.35E-01
    2.90E-01    3.60E-01    -8.99E-04    1.25E+00    1.36E+00    3.34E-01
    2.80E-01    3.57E-01    -8.74E-04    1.28E+00    1.38E+00    3.33E-01
    2.78E-01    3.56E-01    -8.70E-04    1.29E+00    1.39E+00    3.33E-01
    2.63E-01    3.50E-01    -8.20E-04    1.33E+00    1.43E+00    3.31E-01
    2.60E-01    3.48E-01    -8.10E-04    1.35E+00    1.44E+00    3.30E-01
    2.50E-01    3.45E-01    -7.86E-04    1.38E+00    1.47E+00    3.29E-01
    2.40E-01    3.41E-01    -7.71E-04    1.41E+00    1.50E+00    3.27E-01
    2.38E-01    3.40E-01    -7.65E-04    1.42E+00    1.51E+00    3.27E-01
    2.27E-01    3.35E-01    -7.29E-04    1.46E+00    1.54E+00    3.24E-01
    2.20E-01    3.31E-01    -7.23E-04    1.49E+00    1.57E+00    3.22E-01
    2.17E-01    3.30E-01    -7.21E-04    1.50E+00    1.57E+00    3.22E-01
    2.08E-01    3.27E-01    -7.18E-04    1.53E+00    1.60E+00    3.19E-01
    2.00E-01    3.23E-01    -7.17E-04    1.56E+00    1.62E+00    3.17E-01
    1.90E-01    3.20E-01    -7.08E-04    1.59E+00    1.65E+00    3.15E-01
    1.90E-01    3.19E-01    -7.08E-04    1.59E+00    1.65E+00    3.15E-01
    1.82E-01    3.15E-01    -7.01E-04    1.62E+00    1.68E+00    3.13E-01
    1.80E-01    3.14E-01    -7.00E-04    1.63E+00    1.68E+00    3.13E-01
    1.74E-01    3.11E-01    -7.03E-04    1.65E+00    1.70E+00    3.12E-01
    1.70E-01    3.09E-01    -7.02E-04    1.67E+00    1.71E+00    3.11E-01
    1.67E-01    3.08E-01    -7.11E-04    1.68E+00    1.72E+00    3.10E-01
    1.60E-01    3.05E-01    -7.27E-04    1.70E+00    1.74E+00    3.09E-01
    1.54E-01    3.03E-01    -7.56E-04    1.71E+00    1.75E+00    3.07E-01
    1.50E-01    3.02E-01    -7.90E-04    1.72E+00    1.75E+00    3.07E-01
    1.48E-01    3.02E-01    -8.03E-04    1.72E+00    1.76E+00    3.06E-01
    1.43E-01    3.01E-01    -8.36E-04    1.73E+00    1.76E+00    3.05E-01
    1.40E-01    3.00E-01    -8.56E-04    1.74E+00    1.77E+00    3.04E-01
    1.38E-01    3.00E-01    -8.73E-04    1.74E+00    1.77E+00    3.04E-01
    1.33E-01    2.98E-01    -9.00E-04    1.75E+00    1.78E+00    3.03E-01
    1.30E-01    2.97E-01    -9.19E-04    1.76E+00    1.78E+00    3.02E-01
    1.29E-01    2.97E-01    -9.27E-04    1.76E+00    1.78E+00    3.02E-01
    1.25E-01    2.96E-01    -9.53E-04    1.77E+00    1.79E+00    3.01E-01
    1.20E-01    2.94E-01    -9.69E-04    1.78E+00    1.79E+00    3.00E-01
    1.18E-01    2.94E-01    -9.74E-04    1.78E+00    1.80E+00    3.00E-01
    1.11E-01    2.93E-01    -1.00E-03    1.78E+00    1.79E+00    2.99E-01
    1.10E-01    2.93E-01    -1.01E-03    1.78E+00    1.79E+00    2.98E-01
    1.05E-01    2.93E-01    -1.02E-03    1.78E+00    1.79E+00    2.98E-01
    1.00E-01    2.93E-01    -1.04E-03    1.78E+00    1.79E+00    2.97E-01
    9.52E-02    2.92E-01    -1.06E-03    1.78E+00    1.78E+00    2.96E-01
    9.09E-02    2.93E-01    -1.07E-03    1.77E+00    1.78E+00    2.96E-01
    9.00E-02    2.93E-01    -1.07E-03    1.77E+00    1.77E+00    2.96E-01
    8.70E-02    2.93E-01    -1.08E-03    1.76E+00    1.77E+00    2.95E-01
    8.50E-02    2.94E-01    -1.09E-03    1.76E+00    1.76E+00    2.95E-01
    8.33E-02    2.94E-01    -1.09E-03    1.76E+00    1.76E+00    2.95E-01
    8.00E-02    2.95E-01    -1.10E-03    1.75E+00    1.75E+00    2.95E-01
    7.69E-02    2.95E-01    -1.11E-03    1.74E+00    1.74E+00    2.94E-01
    7.50E-02    2.96E-01    -1.11E-03    1.73E+00    1.73E+00    2.94E-01
    7.41E-02    2.96E-01    -1.11E-03    1.73E+00    1.73E+00    2.94E-01
    7.14E-02    2.97E-01    -1.10E-03    1.72E+00    1.72E+00    2.94E-01
    7.00E-02    2.98E-01    -1.10E-03    1.71E+00    1.72E+00    2.95E-01
    6.90E-02    2.98E-01    -1.11E-03    1.71E+00    1.71E+00    2.95E-01
    6.67E-02    2.99E-01    -1.11E-03    1.70E+00    1.70E+00    2.95E-01
    6.50E-02    3.00E-01    -1.11E-03    1.69E+00    1.70E+00    2.95E-01
    6.25E-02    3.01E-01    -1.11E-03    1.68E+00    1.69E+00    2.95E-01
    6.00E-02    3.02E-01    -1.10E-03    1.67E+00    1.68E+00    2.95E-01
    5.88E-02    3.02E-01    -1.10E-03    1.67E+00    1.68E+00    2.95E-01
    5.56E-02    3.03E-01    -1.09E-03    1.65E+00    1.67E+00    2.94E-01
    5.30E-02    3.03E-01    -1.08E-03    1.64E+00    1.66E+00    2.94E-01
    5.00E-02    3.04E-01    -1.06E-03    1.63E+00    1.65E+00    2.94E-01
    4.55E-02    3.05E-01    -1.04E-03    1.61E+00    1.64E+00    2.94E-01
    4.00E-02    3.06E-01    -9.82E-04    1.59E+00    1.62E+00    2.93E-01
    3.57E-02    3.07E-01    -9.48E-04    1.57E+00    1.60E+00    2.93E-01
    3.40E-02    3.08E-01    -9.33E-04    1.56E+00    1.60E+00    2.93E-01
    3.23E-02    3.09E-01    -9.26E-04    1.56E+00    1.59E+00    2.93E-01
    3.00E-02    3.10E-01    -9.15E-04    1.55E+00    1.58E+00    2.92E-01
    2.94E-02    3.10E-01    -9.12E-04    1.54E+00    1.58E+00    2.92E-01
    """)