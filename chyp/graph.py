#     chyp - A compositional hypergraph library
#     Copyright (C) 2022 - Aleks Kissinger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from typing import Set, List, Dict, Iterator, Any

class VData:
    def __init__(self, value: Any="", x: float=0, y: float=0, in_edges: Set[int]=set(), out_edges: Set[int]=set()):
        self.value = value
        self.x = x
        self.y = y
        self.in_edges = in_edges
        self.out_edges = out_edges

class EData:
    def __init__(self, value: Any="", s: List[int]=[], t: List[int]=[], x: float=0, y: float=0, hyper: bool=True):
        self.value = value
        self.x = x
        self.y = y
        self.s = s
        self.t = t
        self.hyper = hyper

class Graph:
    def __init__(self):
        self.vdata: Dict[int, VData] = {}
        self.edata: Dict[int, EData] = {}
        self.vindex = 0
        self.eindex = 0

    def vertices(self) -> Iterator[int]:
        return iter(self.vdata.keys())

    def edges(self) -> Iterator[int]:
        return iter(self.edata.keys())

    def vertex_data(self, v: int) -> VData:
        return self.vdata[v]

    def edge_data(self, e: int) -> EData:
        return self.edata[e]

    def add_vertex(self, ty:int, x:float=0, y:float=0) -> int:
        v = self.vindex
        self.vindex += 1
        self.vdata[v] = VData(ty, x, y)
        vd = VData(ty, x, y)
        return v

    def add_hedge(self, ty:int, s:List[int], t:List[int], x:float=0, y:float=0) -> int:
        e = self.eindex
        self.eindex += 1
        self.edata[e] = EData(ty, s, t, x, y)
        for v in s: self.vdata[v].out_edges.add(e)
        for v in t: self.vdata[v].in_edges.add(e)
        return e

    def add_edge(self, ty:int, s:int, t:int) -> int:
        e = self.add_hedge(ty, [s], [t])
        self.edata[e].hyper = False
        return e
