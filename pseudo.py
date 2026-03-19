def find_centroid():
    # this function finds the centroid of a tree (can be one or 2)
    # check for one node graph early

    # create a py-dictnry degree of each node
    # create a queue with all leafs
    # to remember how many nodes are left, set a variable remaining_nodes

    # jab tak remaining_nodes > 2:
        # remove all current leaves
        # decrease remaining_nodes accordingly
        # for every removed leaf:
            # degree of its neighbors -= 1 
            # agar any neighbor becomes a leaf put it in next queue
    # Return remaining nodes in queue (centroids)
    pass

def root_tree():
    # this function tree ko root pe baithata hai (BFS style, no recursion)

    # init children dict (node -> childer)
    # init level dict (root ka level = 0)
    # create bfs_order list (to tracking)
    # queue bana lo BFS ke liye
    # visited set 

    # until queue exists:
        # ek node remove
        # check neighbors
        # if neighbor visited nahi hai:
            # put in visited
            # current node's child
            # level = parent + 1
            # put in bfs_order
            # queue in

    # return children, bfs_order, level 
    pass

def ahu_label():
    #  function bottom-up labeling (AHU style swag)
    # leaves -> root labeling

    # python-dict for node-label

    # reverse bfs_order
    # for every node
        # check level
        # check label childern
        # sort and make a tuple (mastermind work) (signature)

        # is no mapping of this level, then init:
            #(level -> dict)

        # never signature like this already
            # new label assign (increment style)

        # give current node a label

    # return label dict
    pass

def _compare():
    # to compare rooted trees
    # will try to map both similarly (shared mapping)

    # create shared_mapping structure 

    # max depth of both trees

    # group trees nodes level wise

    # create label1 and label2

    # start from deepest level:
        # create level_map (signature -> label)

        # process tree 1 ke nodes:
            # create signature from children labels
            # if signature new:
                # new label
            # store in label1

        # process tree2 and store in label2 (same level_map)

        # save label maps

    # compare root labels
    # if same then voila isomorphic, else sad life
    pass

def are_isomorphic():
    # main function to be used

    # verify node count
    # if one node only, then true

    # find centroids
    # if centroid count don't match fail

    # helper function to check pair
        # root trees on given centroids
        # run compare function
        # return result

    # if only one centroid, direct:
        # direct check_pair chalao

    # if 2 centroids :
        # try first pairing
        # else second pairing try

    # final result

    pass
