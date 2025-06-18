import yaml
import os
from collections import defaultdict, deque

def get_package_info(file_path):
    """Parses an ato.yaml file to extract package identifier and dependencies."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        package_identifier = data.get('package', {}).get('identifier')
        dependencies = []
        if data.get('dependencies'):
            for dep in data.get('dependencies', []):
                # Ensure dependency entry and its identifier are valid
                if isinstance(dep, dict) and dep.get('identifier'):
                    dependencies.append(dep.get('identifier'))
        return package_identifier, dependencies
    except yaml.YAMLError as e:
        print(f"Error parsing YAML from {file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while reading {file_path}: {e}")
    return None, []

def main():
    """
    Determines and prints the build order of atopile packages based on local dependencies.
    Outputs package paths relative to the repository root, one per line.
    """
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    packages_base_dir = "packages"  # Assuming your packages are in a 'packages' subdirectory
    search_dir = os.path.join(repo_root, packages_base_dir)

    package_files = []
    for root_dir, _, files in os.walk(search_dir):
        for file in files:
            if file == "ato.yaml":
                package_files.append(os.path.join(root_dir, file))

    if not package_files:
        print(f"No ato.yaml files found in {search_dir}")
        return

    package_info = {}  # Maps identifier to {'path': rel_path, 'deps': [dep_ids]}
    local_package_identifiers = set() # Set of all identifiers defined in this repo

    for f_path in package_files:
        identifier, deps = get_package_info(f_path)
        if identifier:
            # Store path relative to repo root (e.g., "packages/my_package")
            package_dir_abs = os.path.dirname(f_path)
            relative_package_dir = os.path.relpath(package_dir_abs, repo_root)
            
            package_info[identifier] = {'path': relative_package_dir, 'deps': deps}
            local_package_identifiers.add(identifier)
        else:
            print(f"Warning: Could not reliably read package identifier from {f_path}")

    # Build dependency graph for local packages
    adj_list = defaultdict(list)  # Maps a package to packages that depend on it
    in_degree = defaultdict(int)  # Maps a package to how many local packages it depends on

    all_graph_nodes = set()

    for identifier, info in package_info.items():
        all_graph_nodes.add(identifier) # Ensure all packages are nodes in the graph
        if identifier not in in_degree:
             in_degree[identifier] = 0 # Initialize in_degree for all nodes
        for dep_identifier in info['deps']:
            if dep_identifier in local_package_identifiers:  # Only consider internal dependencies
                # If 'identifier' depends on 'dep_identifier', edge is dep_identifier -> identifier
                adj_list[dep_identifier].append(identifier)
                in_degree[identifier] += 1
            # External dependencies (not in local_package_identifiers) are ignored for ordering

    # Topological sort
    queue = deque([node for node in all_graph_nodes if in_degree[node] == 0])
    sorted_order_identifiers = []
    
    while queue:
        node_id = queue.popleft()
        sorted_order_identifiers.append(node_id)
        
        for dependent_package_id in adj_list[node_id]:
            in_degree[dependent_package_id] -= 1
            if in_degree[dependent_package_id] == 0:
                queue.append(dependent_package_id)
                
    if len(sorted_order_identifiers) != len(all_graph_nodes):
        missing_nodes = all_graph_nodes - set(sorted_order_identifiers)
        print(f"Error: Cycle detected in dependencies or orphaned packages. Cannot determine build order.")
        print(f"  Processed nodes: {sorted_order_identifiers}")
        print(f"  Nodes not processed (part of cycle or an issue): {missing_nodes}")
        # To help debug, print in_degrees of missing nodes
        for m_node in missing_nodes:
            print(f"    - {m_node} (in-degree: {in_degree.get(m_node, 'N/A')})")
        return

    # Output the ordered relative package paths
    for identifier in sorted_order_identifiers:
        path_to_print = package_info[identifier]['path']
        if path_to_print: # Ensure path is not empty
             print(path_to_print)

if __name__ == "__main__":
    main()
