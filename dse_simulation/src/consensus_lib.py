import roslib
import sys
import rospy
import numpy as np
import datetime
import time
from geometry_msgs.msg import Pose
from dse_msgs.msg import PoseMarkers
from std_msgs.msg import Float64MultiArray
from std_msgs.msg import MultiArrayLayout
from std_msgs.msg import MultiArrayDimension
from dse_msgs.msg import InfFilterPartials
from dse_msgs.msg import InfFilterResults
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt

import dse_constants

#
# # Grab the agent with a specific ID
# # Done by looping through the list of agents and checking the ID
# def agent_with_id(agents, ID):
#     for i in range(np.shape(agents)[0]):
#         if agents[i].objectID == ID:
#             agent = agents[i]
#             return
#     agent = []


# Ensures that every agent has the same state variables in the same order
def get_sorted_agent_states(array_ids, array_Y, array_y, array_I, array_i, dim_state):

    # Build combined list of ids
        # Still trying to come up with a way to take in data of any form and return vector of ids
    flat_list = [item for sublist in array_ids for item in sublist]
    id_list = np.unique(flat_list)
    id_list = np.sort(id_list)
    n_agents = len(id_list)

    # Ensure all agents' state variables match the master list
    # For each agent that sent in data
    for i in range(len(array_ids)):

        # If the state variable isn't correct, re-order/extend it
        if not np.array_equal(id_list, array_ids[i]):

            # Build an empty set of variables
            # Full-size, ready for data to be inserted
            # Potentially change the initialization?
            master_Y = 0.01 * np.eye(n_agents * dim_state)
            master_y = np.zeros((n_agents * dim_state, 1))
            master_I = np.zeros((n_agents * dim_state, n_agents * dim_state))
            master_i = np.zeros((n_agents * dim_state, 1))

            # Move the agents' values to the location specified in the master list
            # Loop through the input data in chunks of (state_dim x state_dim)
                # Take each block and move it to the correct location in the master arrays

            for agent_row_index in range(len(array_ids[i])):
                for agent_column_index in range(len(array_ids[i])):

                    # Given a chunk of data and a row and column index,
                    # grab the row and column ids of the input data
                    # Find the location of those ids in the master arrays
                    group_row_index = np.where(id_list == array_ids[i][agent_row_index])[0][0]
                    group_column_index = np.where(id_list == array_ids[i][agent_column_index])[0][0]

                    # Generate indices (to make the assignment step shorter)
                    g_row_lo = dim_state * group_row_index
                    g_row_hi = g_row_lo + dim_state
                    g_col_lo = dim_state * group_column_index
                    g_col_hi = g_col_lo + dim_state
                    a_row_lo = dim_state * agent_row_index
                    a_row_hi = a_row_lo + dim_state
                    a_col_lo = dim_state * agent_column_index
                    a_col_hi = a_col_lo + dim_state

                    # Move this chunk of data to the master arrays
                    master_Y[g_row_lo:g_row_hi, g_col_lo:g_col_hi] = array_Y[i][a_row_lo:a_row_hi, a_col_lo:a_col_hi]
                    master_I[g_row_lo:g_row_hi, g_col_lo:g_col_hi] = array_I[i][a_row_lo:a_row_hi, a_col_lo:a_col_hi]

                master_y[g_row_lo:g_row_hi] = array_y[i][a_row_lo:a_row_hi]
                master_i[g_row_lo:g_row_hi] = array_i[i][a_row_lo:a_row_hi]

            array_ids[i] = id_list
            array_Y[i] = master_Y
            array_y[i] = master_y
            array_I[i] = master_I
            array_i[i] = master_i

    return array_ids, array_Y, array_y, array_I, array_i

#
# # Update the momory_id_comm list in each agent to include each agent they
# # can communicate with (based on a communication model).
# def apply_comm_model_obs(agents):
#
#     # Apply communication model and create list of agents each agent can communicate with
#     # Current communication model is the same as the observation model
#     agents_arr = []
#     for agent = agents:
#         agents_arr = [agents_arr, agent[1]]
#
#     for agent = agents_arr:
#         agent.memory_id_comm = []
#         for i in range(np.shape(agent.memory_id_obs)[0]):
#             if not isempty(agent_with_id(agents_arr, agent.memory_id_obs[i])):
#                 agent.memory_id_comm = [agent.memory_id_comm, agent.memory_id_obs[i]]


# Update the momory_id_comm list in each agent to include each agent they
# can communicate with (based on a communication model).
def apply_comm_model(SIM, agents, comm_list):

    # Apply communication model and create list of agents each agent can communicate with
    # Current communication model is the same as the observation model
    agents_arr = []
    for id in range(np.shape(agents)[0]):
        agent = agents[id]
        if SIM.OBJECTS(agent.objectID).type == 1:
            agents_arr = [agents_arr, agent]

    for index in range(np.shape(agents_arr)[0]):
        agent = agents_arr(index)
        agent_comm_list = cell2mat(comm_list[index])
        agent.memory_id_comm = agent_comm_list


# Update the momory_id_comm list in each agent to include each agent they
# can communicate with.
def apply_comm_model_distance(SIM, agents, threshold):

    agents_arr = []
    for id in range(np.shape(agents)[0]):
        agent = agents[id]
        if SIM.OBJECTS(agent.objectID).type == 1:
            agents_arr = [agents_arr, agent]

    for i in range(np.shape(agents_arr)[0]):
        agents_arr[i].memory_id_comm = []
        for j in range(np.shape(agents_arr)[0]):
            if i != j:
                detect = agents_arr[i].commRadius
                Xi = SIM.OBJECTS[agents_arr[i].objectID].X
                Xj = SIM.OBJECTS[agents_arr[j].objectID].X
                if norm(Xj[1: 3] - Xi[1:3]) <= detect:
                    agents_arr[i].memory_id_comm = [agents_arr[i].memory_id_comm, j]

#
# # Break agents up into groups based on communication graph
# def break_agents_into_groups(SIM, agent_data):
#     # Split into groups of agents that can communicate with eachother,
#     # and puts those agents in a group. Continues this along the chain
#     # until there are no more agents in this group, then finds the other
#     # isolated groups.
#
#     agent_groups = []
#     num_groups = 0
#     # While there are still agents to group up
#     while numel(agent_data) > 0:
#
#         # Start with the first remaining agent
#         group = agent_data[1]
#         id_obs = group(1).memory_id_comm
#         new_group = 1
#         agent_data[1] = []
#
#         # while there are new agents in the group
#         while new_group > 0:
#
#             # Get a list of the newly-observed IDs
#             len = numel(group)
#             tmp = group[1, len - new_group + 1:len]
#             id_obs_new = []
#             for m in range(np.shape(tmp)[0]):
#                 id_obs_new = [id_obs_new, tmp(m).memory_id_comm]
#
#             id_obs_new = sort(unique(id_obs_new))
#             id_obs_new = setdiff(id_obs_new, id_obs)
#             id_obs = sort([id_obs, id_obs_new])
#             new_group = 0
#             indices = []
#
#             # Get the agents with ids matching the observed list
#             for i in id_obs:
#                 for j in range(np.shape(agent_data)[0]):
#                     if agent_data[j].objectID == i:
#                         group = [group, agent_data[j]]
#                         new_group = new_group + 1
#                         indices = [indices, j]
#
#             # Remove grouped agents from the general pool
#             for i in sort(indices, 'descend'):
#                 agent_data[i] = []
#
#         agent_groups[num_groups + 1] = group
#         num_groups = num_groups + 1

# INPUT -
#   The 4 information variables from each agent in this group
#   The current consensus step number
#   The total number of consensus steps
# RETURNS -
#   The updated 4 information variables from each agent in this group
#
# Algorithm
#   Create an undirected communication adjacency matrix for this group
#   create a graph based on this adjacency matrix
#   for each agent in thr group:
#       for each agent this agent can communicate with (from adjacency matrix):
#           Store their prior
#       Compute CI weights based on those priors
#       Apply those weights ad compute this agent's new y, Y
#       for each agent in the group: # This includes the agent itself
#           i, I += (i, I)*graph.p
#       y, Y = y, Y + (percentage of consensus steps run) * (i, I)

# Perform one consensus step
def consensus_step(array_ids, array_Y, array_y, array_I, array_i, array_comm, dim_state, step, num_steps):
    # Perform consensus computations

    ## Initialize Graph
    # Generate graph
    # Create adjacency matrix
    # use generate_graph function
    adj = apply_comm_model_distance()
    graph_p, graph_d = generate_graph(adj)
    size_comp, nComponents, members = networkComponents(p)

    ## Compute and store consensus variables
    for i in range(np.shape(array_Y)[0]):

        # Grab variables from neighboring agents
        Y_local = []
        y_local = []
        idx_neighbors = agents[i].memory_id_comm

        for j in range(np.shape(idx_neighbors)[0]):
            agent = agent_with_id(agents, idx_neighbors[j])
            Y_local[:,:, j] = (agent.memory_Y)
            y_local[:,:, j] = (agent.memory_y)

        # Compute and apply CI weights
        [weights_ci, Y_prior, y_prior] = calc_ci_weights_simple(Y_local, y_local, 'det')

        delta_I = zeros(size(agents[1].memory_I))
        delta_i = zeros(size(agents[1].memory_i))

        for j in range(np.shape(agents)[0]):
            p_jk = graph_p[i, j]

            delta_I = delta_I + p_jk * agents[j].memory_I
            delta_i = delta_i + p_jk * agents[j].memory_i

        ratio = step / num_steps
        Y = Y_prior + ratio * size_comp[i] * delta_I
        y = y_prior + ratio * size_comp[i] * delta_i

        # consensus_data[i].Y = Y
        # consensus_data[i].y = y
        # consensus_data[i].Y_prior = Y_prior
        # consensus_data[i].y_prior = y_prior
        # consensus_data[i].delta_I = delta_I
        # consensus_data[i].delta_i = delta_i

    return # consensus_data


def consensus(agent_groups):
    num_steps = 20
    adj = apply_comm_model_distance()
    [p, d] = generate_graph(adj)
    graph = [adj, p, d]
    size_comp, nComponents, members = networkComponents(p)
    for i in range(num_steps):
        consensus_step(agent_groups[group_num], i, num_steps, graph, size_comp)

    for group_num in range(np.shape(agent_groups)[0]):
        if numel(agent_groups[group_num]) == 1:
            agent_groups[group_num].memory_Y = agent_groups[group_num].memory_Y + agent_groups[group_num].memory_I
            agent_groups[group_num].memory_y = agent_groups[group_num].memory_y + agent_groups[group_num].memory_i
            agent_groups[group_num].memory_P = np.linalg.inv(agent_groups[group_num].memory_Y)
            agent_groups[group_num].memory_x = np.linalg.inv(agent_groups[group_num].memory_Y) *agent_groups[group_num].memory_y
        else:
            # Compute first consensus step
            step = 1
            for i in range(np.shape(agent_groups[group_num])[0]):
                consensus_data[step, group_num][i].Y_prior = agent_groups[group_num][i].memory_Y
                consensus_data[step, group_num][i].y_prior = agent_groups[group_num][i].memory_y
                consensus_data[step, group_num][i].delta_I = agent_groups[group_num][i].memory_I
                consensus_data[step, group_num][i].delta_i = agent_groups[group_num][i].memory_i

            # Compute the remaining consensus steps
            for step in range(2, num_steps):
                consensus_data[step, group_num] = consensus_step(agent_groups[group_num], step, num_steps)

            # After all agents' variables have been computed, store them
            for i in range(np.shape(consensus_data[step, group_num])[0]):
                agent_groups[group_num][i].memory_Y = consensus_data[step, group_num][i].Y_prior
                agent_groups[group_num][i].memory_y = consensus_data[step, group_num][i].y_prior
                agent_groups[group_num][i].memory_I = consensus_data[step, group_num][i].delta_I
                agent_groups[group_num][i].memory_i = consensus_data[step, group_num][i].delta_i

            # Store final consensus in each agent
            for i in range(np.shape(consensus_data[step, group_num])[0]):
                agent_groups[group_num][i].memory_Y = consensus_data[step, group_num][i].Y
                agent_groups[group_num][i].memory_y = consensus_data[step, group_num][i].y
                agent_groups[group_num][i].memory_P = np.linalg.inv(consensus_data[step, group_num][i].Y)
                agent_groups[group_num][i].memory_x = np.linalg.inv(consensus_data[step, group_num][i].Y) * consensus_data[step, group_num][i].y

    return agent_groups


# function [gt_estimation] = gt(agent_data)
#     y = y_1 + i_1 + i_2
# 
def position_from_id(agent, id):

    x = agent.memory_x
    index_id = find(id == agent.memory_id_list)
    index_agent = find(agent.objectID == agent.memory_id_list)
    dim_state = agent.dim_state

    # Generate indices (to make the assignment setp shorter)
    meas_low = dim_state * (index_id - 1) + 1
    meas_high = dim_state * index_id
    agent_low = dim_state * (index_agent - 1) + 1
    agent_high = dim_state * index_agent

    rel_pos = x[meas_low:meas_high] - x[agent_low:agent_high]
    rel_pos = rel_pos[1:2]

    return rel_pos

# [nComponents,sizes,members] = networkComponents(A)
#
# Daniel Larremore
# April 24, 2014
# larremor@hsph.harvard.edu
# http://danlarremore.com
# Comments and suggestions always welcome.
#
# INPUTS:
# A                     Matrix. This function takes as an input a
# network adjacency matrix A, for a network that is undirected. If you
# provide a network that is directed, this code is going to make it
# undirected before continuing. Since link weights will not affect
# component sizes, weighted and unweighted networks work equally well. You
# may provide a "full" or a "sparse" matrix.
#
# OUTPUTS:
# nComponents             INT - The number of components in the network.
# sizes                 vector<INT> - a vector of component sizes, sorted,
#   descending.
# members               cell<vector<INT>> a cell array of vectors, each
#   entry of which is a membership list for that component, sorted,
#   descending by component size.
#

def networkComponents(A):
    # Number of nodes
    N = np.shape(A)[0]
    # Remove diagonals
    np.fill_diagonal(A, 0)
    # make symmetric, just in case it isn't
    A = np.add(A, A.T)
    # Have we visited a particular node yet?
    isDiscovered = np.zeros(N)
    # Empty members cell
    members = []
    # check every node
    for n in range(N):
        if not isDiscovered[n]:
            # started a new group so add it to members
            members.append([n])
            # account for discovering n
            isDiscovered[n] = 1
            # set the ptr to 1
            ptr = 0
            while (ptr < len(members[-1])):
                # find neighbors
                nbrs = np.array(np.where(A[:, members[-1][ptr]] != 0))
                # here are the neighbors that are undiscovered
                newNbrs = nbrs[isDiscovered[nbrs] == 0]
                # we can now mark them as discovered
                isDiscovered[newNbrs] = 1
                # add them to member list
                members[-1].extend(newNbrs)
                # increment ptr so we check the next member of this component
                ptr += 1

    # number of components
    nComponents = len(members)
    size_group = np.zeros(N)
    for n in range(nComponents):
        # compute sizes of components
        group_n = members[n]
        for j in range(len(group_n)):
            size_group[group_n[j]] = len(group_n)
        #     sizes(n) = length(members[n])

    return size_group, nComponents, members

# Computes the consensus weights (p)
# and the inclusive degree of each node (d)
#   It computes the degree of each node and adds 1, assuming the graph is not self-connected at the start
def generate_graph(adj):
    # This function accepts an adjecancy matrix where degree of each
    # node is equal to 1 + number of its neighbours. That is, all agents
    # are connected to themselves as well.

    #  number of nodes ( = |v|)
    nv = np.shape(adj)[0]

    # Remove diagonals
    np.fill_diagonal(adj, 0)

    d = np.zeros(nv)
    # Calculate inclusive node degrees
    for i in range(nv):
        d[i] = np.sum(adj[i, :]) + 1

    # Calculate weights for MHMC distributed averaging
    # This is slightly different from the formula used in the paper
    # http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.161.3893&rep=rep1&type=pdf
    p = np.zeros(np.shape(adj))
    for i in range(nv):
        for j in range(nv):
            if adj[i, j] != 0:
                if i != j:
                    p[i, j] = min(1 / d[i], 1 / d[j])
            else:
                p[i, j] = 0

    for i in range(nv):
        p[i, i] = 1 - np.sum(p[i, :])

    return p, d

# Not required - As long as weights add to 1, it's fine. ex: 1/n
# Optimization
#   S1 - Information matrices
#   local_inf_vec - Information vectors
#   method_ - string defining the method (determinant, trace...)
# scipy.optimize.minimize
def calc_ci_weights_simple(S1, local_inf_vec, method_):
    n_agents = np.shape(local_inf_vec)[0]

    # CI weghts
    weights_ci = np.full(n_agents, 1.0 / n_agents)

    # Now that we have the weights, calculate w1*I1+...+wn*In
    inf_vec = np.zeros(np.shape(local_inf_vec[0]))
    for i in range(len(weights_ci)):
        inf_vec = np.add(inf_vec, weights_ci[i] * local_inf_vec[i])

    inf_mat = np.zeros(np.shape(S1[0]))
    for i in range(len(weights_ci)):
        inf_mat = np.add(inf_mat, weights_ci[i] * S1[i])
    # Ensure that the matrix is symmetric
    inf_mat = 0.5 * np.sum(inf_mat, inf_mat.T)

    return weights_ci, inf_mat, inf_vec

# def calc_ci_weights_ver3(S1, local_inf_vec, method_):
#     # Number of covariance matrices
#     nCovSamples = size(S1, 3)
#
#     # Generate a random initialize weight and normalize it so
#     # it sums up to 1.
#     x0 = rand(nCovSamples, 1)
#     x0 = x0 ./ sum(x0)
#
#     # Thos constraint ensures that the sun of the weights is 1
#     Aeq = ones(size(x0))'
#     beq = 1
#
#     # Weights belong to the interval [0,1]
#     lb = zeros(size(x0))'
#     ub = ones(size(x0))'
#     A = []
#     b = []
#     nonlcon = []
#
#     if verLessThan('matlab', '8.4'):
#         options = optimset('Algorithm', 'sqp')
#
#         if strcmp(method_, 'tr'):
#             x = fmincon(@cost_ci_tr, x0, A, b, Aeq, beq, lb, ub, nonlcon, options)
#         elif strcmp(method_, 'det'):
#             x = fmincon(@cost_ci_det, x0, A, b, Aeq, beq, lb, ub, nonlcon, options)
#
#     else:
#         options = optimoptions('fmincon', 'Display', 'none', 'Algorithm', 'sqp')
#
#         if strcmp(method_, 'tr'):
#             x = fmincon(@cost_ci_tr, x0, A, b, Aeq, beq, lb, ub, nonlcon, options)
#         elif strcmp(method_, 'det'):
#             x = fmincon(@cost_ci_det, x0, A, b, Aeq, beq, lb, ub, nonlcon, options)
#
#     # CI weghts
#     weights_ci = x
#
#     # Normalize just in case
#     if sum(weights_ci) > 1:
#         weights_ci = weights_ci ./ sum(weights_ci)
#
#     # Now that we have the weights, calculate w1*I1+...+wn*In
#     inf_vect = special_dot_sum(weights_ci, local_inf_vec, 0)
#     inf_mat = calc_inf_ci(x)
#
#     return weights_ci, inf_mat, inf_vect


# Trace cost function as the objective function
# def cost_ci_tr(x):
#     information_matrix = zeros(size(S1[:, :, 1]))
#
#     for i_tr in range(length(x)):
#         information_matrix = information_matrix + x[i_tr, 1] * (S1[:, :, i_tr])
#
#     # Make the information matrix symetric in case numerical errors during the summation calculation
#     information_matrix = 0.5 * (information_matrix + information_matrix')
#
#     cost_tr = trace(np.linalg.inv(information_matrix))
#     return cost_tr


# # Determinant cost function
# def cost_ci_det(x):
#     information_matrix = zeros(size(S1[:, :, 1]))
#
#     for i_det in range(length(x)):
#         information_matrix = information_matrix + x[i_det, 1] * (S1[:, :, i_det])
#
#     # Make the information matrix symetric in case numerical errors during the summation calculation
#     information_matrix = 0.5 * (information_matrix + information_matrix')
#
#     cost_det = -log(det(information_matrix))
#
#     # cost calculation near the singularity.
#     if isinf(cost_det):
#         cost_det = log(det(np.linalg.inv(information_matrix)))
#
#     return cost_det
#
#
# def calc_inf_ci(x):
#     information_matrix = zeros(size(S1[:, :, 1]))
#
#     for i_det in range(length(x)):
#         information_matrix = information_matrix  +x[i_det, 1] * (S1[:, :, i_det])
#
#     # Make the information matrix symetric in case numerical errors during the summation calculation
#     information_matrix = 0.5 * (information_matrix + information_matrix')
#
#     return information_matrix

