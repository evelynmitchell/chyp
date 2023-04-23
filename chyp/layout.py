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
import math
import cvxpy as cp
from cvxpy.expressions.variable import Variable
from cvxpy.expressions.constants.constant import Constant
from cvxpy.problems.objective import Minimize
from cvxpy.problems.problem import Problem

from .graph import Graph
from .term import layer_decomp

def convex_layout(g: Graph):
    """A layout based on `layer_decomp` and convex optimisation

    Vertices and edges are placed in layers according to `layer_decomp`. Their
    y-coordinates are chosen by convex optimation to try to make connections as
    straight as possible subject to the constraints:
      1. vertices must be in order and at least 1.0 apart
      2. edges must be in order and not overlapping
    """
    v_layers, e_layers = layer_decomp(g)

    # initialise x-coordinates and rough y-coordinates
    x = -(len(v_layers) - 1) * 1.5
    for layer in range(len(v_layers)):
        for i, v in enumerate(v_layers[layer]):
            vd = g.vertex_data(v)
            vd.x = x if layer == 0 or layer == len(v_layers)-1 else x - 0.8
            vd.y = i - (len(v_layers[layer])-1)/2
        if layer >= len(e_layers): break
        for i, e in enumerate(e_layers[layer]):
            ed = g.edge_data(e)
            ed.x = x + 1.5
            ed.y = 2 * i - (len(e_layers[layer])-1)
        x += 3.0

    if g.num_vertices() == 0 or g.num_edges() == 0: return

    # solve for better y-coordinates using convex optimisation
    
    # variables for the y-coordinates of vertices/edges
    vy = Variable(g.num_vertices(), 'vy')
    ey = Variable(g.num_edges(), 'ey')

    # maintain a table from vertex/edge names to variable indices
    vtab = { v : i for i, v in enumerate(g.vertices()) }
    etab = { e : i for i, e in enumerate(g.edges()) }

    constr = []
    opt = []
    for layer in range(len(v_layers)):
        v_layer = v_layers[layer]
        for i in range(len(v_layer)-1):
            v1 = v_layer[i]
            v2 = v_layer[i+1]
            constr.append(vy[vtab[v2]] - vy[vtab[v1]] >= Constant(1))

        # break if this is the final v_layer (hence no more e_layers)
        if layer >= len(e_layers): break
        e_layer = e_layers[layer]

        for i in range(len(e_layer)):
            e1 = e_layer[i]
            for vlist, weight in ((g.source(e1), 1.0), (g.target(e1), 2.0)):
                for j, v in enumerate(vlist):
                    y_shift = Constant(0.0 if len(vlist) <= 1 else ((j / (len(vlist) - 1)) - 0.5))
                    opt.append(Constant(weight) * (vy[vtab[v]] - (ey[etab[e1]] + y_shift)))

            if i+1 >= len(e_layer): break
            e2 = e_layer[i+1]
            dist = (g.edge_data(e1).box_size() + g.edge_data(e2).box_size()) * 0.5
            constr.append(ey[etab[e2]] - ey[etab[e1]] >= Constant(dist))

    # problem = Problem(Minimize(cp.sum_squares(cp.vstack(opt))), constr)
    problem = Problem(Minimize(cp.norm1(cp.vstack(opt))), constr)
    problem.solve()
    min = None
    max = None
    for v,i in vtab.items():
        y = vy.value[i]
        if min is None or y < min: min = y
        if max is None or y > max: max = y
        g.vertex_data(v).y = y

    if not min is None and not max is None:
        yshift = (min + max) * 0.5
        for v in g.vertices():
            g.vertex_data(v).y -= yshift
    else:
        yshift = 0

    for e,i in etab.items():
        y = ey.value[i]
        g.edge_data(e).y = y - yshift


def layer_layout(g: Graph):
    """A simple layout using `layer_decomp`.

    Vertices are evenly spaced around the x-axis and edges are placed
    as close to the average y-coordinate of their inputs as possible.
    """
    v_layers, e_layers = layer_decomp(g)
    x = -(len(v_layers) - 1) * 1.5
    for l in range(len(e_layers)):
        v_layer = v_layers[l]
        e_layer = e_layers[l]
        for i, v in enumerate(v_layer):
            vd = g.vertex_data(v)
            vd.x = x
            vd.y = i - ((len(v_layer) - 1) * 0.5)

        # place edges, starting from the middle and working outward
        end = len(e_layer)
        start = math.ceil(end/2)

        max_y = 0 # max y-coordinate for edges above the middle
        min_y = 0 # min y-coordinate for edges below the middle

        # for an odd number of edges, place the middle edge first
        if start > end/2:
            i = start-1
            ed = g.edge_data(e_layer[i])
            ed.x = x + 1.5
            ed.y = sum(g.vertex_data(v).y for v in ed.s)/len(ed.s) if len(ed.s) != 0 else 0
            pad = ed.box_size() * 0.5
            min_y = pad
            max_y = -pad

        for i1 in range(start, end):
            i0 = end - i1 - 1

            # place one edge above max_y
            ed = g.edge_data(e_layer[i0])
            pad = ed.box_size() * 0.5
            ed.x = x + 1.5
            ed.y = min(max_y - pad,
                       sum(g.vertex_data(v).y for v in ed.s)/len(ed.s)
                           if len(ed.s) != 0 else 0)
            max_y = ed.y - pad

            # place one edge below min_y
            ed = g.edge_data(e_layer[i1])
            pad = ed.box_size() * 0.5
            ed.x = x + 1.5
            ed.y = max(min_y + pad,
                       sum(g.vertex_data(v).y for v in ed.s)/len(ed.s)
                           if len(ed.s) != 0 else 0)
            min_y = ed.y + pad

        x += 3.0

    for i, v in enumerate(v_layers[-1]):
        vd = g.vertex_data(v)
        vd.x = x
        vd.y = i - ((len(v_layers[-1]) - 1) * 0.5)




# def ready_edges(g: Graph, edges: Set[int], v_done: Set[int]) -> Set[int]:
#     ready = set()
#     for e in edges:
#         src = g.source(e)
#         if all(v in v_done for v in src):
#             ready.add(e)
#     return ready
#
# def layer_layout(g: Graph):
#     """A simple hypergraph layout into evenly-spaced layers
#
#     This layout adds identity boxes if wires need to cross more than one layer, and generally places vertices
#     and boxes as early and near the x-axis as possible. It will throw an exception if the given graph is not
#     directed acyclic.
#
#     Currently it assumes graphs are monogamous. Expect strange behaviours if this is not the case.
#     """
#     layer = list(g.inputs())
#     v_done = set(layer)
#     edges = set(g.edges())
#     new_ids = set()
#
#     x = 0
#     while len(edges) > 0:
#         for i, v in enumerate(layer):
#             g.vertex_data(v).x = x
#             g.vertex_data(v).y = i - (len(layer) - 1)/2
#
#         new_layer = []
#         for i, e in enumerate(ready_edges(g, edges, v_done)):
#             src = g.source(e)
#             c = sum(g.vertex_data(v).y for v in src) / len(src) if len(src) != 0 else 0
#             new_layer.append((c, e, g.target(e)))
#             edges.remove(e)
#         if all(e in new_ids for _, e, _ in new_layer):
#             raise ValueError("Could not make progress. Is graph acyclic?")
#
#         # sort according to center coordinate
#         list.sort(new_layer)
#
#         # for c, e, _ in new_layer:
#         #     print("before " + str(e) + ":" + str(g.edge_data(e)) + " center " + str(c))
#
#         min = 0
#         max = 0
#         ctr = -1
#
#         # forward pass, making enough space by shifting things below the x-axis down
#         for i in range(len(new_layer)):
#             c, e, vs = new_layer[i]
#             pad = (g.edge_data(e).box_size() / 2)
#             if ctr == -1:
#                 # the center should be the first place we cross the x-axis or the last element in the list
#                 if c >= 0 or i == len(new_layer) - 1:
#                     ctr = i
#                     max = c - pad
#                     min = c + pad
#             else:
#                 if c < min + pad:
#                     c = min + pad
#                     min = c + pad
#                     new_layer[i] = (c, e, vs)
#
#         # backward pass, shifting things above the x-axis up
#         for i in range(ctr-1, -1, -1):
#             c, e, vs = new_layer[i]
#             pad = (g.edge_data(e).box_size() / 2)
#             if c > max - pad:
#                 c = max - pad
#                 max = c - pad
#                 new_layer[i] = (c, e, vs)
#
#         layer = []
#         for c, e, vs in new_layer:
#             g.edge_data(e).x = x + 1.5
#             g.edge_data(e).y = c
#             # print("after " + str(e) + ":" + str(g.edge_data(e)) + " center " + str(c))
#             for v in vs:
#                 layer.append(v)
#                 v_done.add(v)
#
#         ready = ready_edges(g, edges, v_done)
#         outputs = set(g.outputs())
#         for v in layer:
#             if (v in outputs and len(edges) > 0) or any(e not in ready for e in g.out_edges(v)):
#                 id = g.insert_id_after(v)
#                 edges.add(id)
#                 new_ids.add(id)
#
#         x += 3
#
#     layer = g.outputs()
#     for i, v in enumerate(layer):
#         g.vertex_data(v).x = x
#         g.vertex_data(v).y = i - (len(layer) - 1)/2
#
#     shift = math.floor(x / 2)
#     for v in g.vertices(): g.vertex_data(v).x -= shift
#     for e in g.edges(): g.edge_data(e).x -= shift
#