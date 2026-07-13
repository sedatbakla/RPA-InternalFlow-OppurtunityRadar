# Import helper functions to retrieve data from the SQLite database.
from database import get_all_flows, get_taxonomy,save_classification

flows = get_all_flows()


taxonomy = get_taxonomy()

def classify_flow(flow_name, taxonomy):

    for _, row in taxonomy.iterrows():  # Iterate through every row in the taxonomy.

        keyword = row["Keyword"]     # Get the keyword and its corresponding capability.

        capability = row["Capability"]

     # Check whether the keyword exists in the flow name.
     # The comparison is case-insensitive.
        if keyword.lower() in flow_name.lower():

            return capability


    # Return "Other" if no keyword matches the flow name.
    return "Other"



# Apply the classification function to every flow name
# and create a new "Capability" column.

flows["Capability"] = flows["Flow Name"].apply(
    lambda x: classify_flow(x, taxonomy)
)

classification_df = flows[
    ["Flow Name", "Capability"]
]

save_classification(classification_df)

print(flows.head())

