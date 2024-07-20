# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""A module containing build_steps method definition."""

from graphrag.index.config import PipelineWorkflowConfig, PipelineWorkflowStep
from typing import Optional

workflow_name = "create_final_entities"

def build_steps(
    config: PipelineWorkflowConfig,
) -> list[PipelineWorkflowStep]:
    """
    Create the final entities table.

    ## Dependencies
    * `workflow:create_base_entity_graph`
    """
    base_text_embed = config.get("text_embed", {})
    entity_name_embed_config = config.get("entity_name_embed", base_text_embed)
    entity_name_description_embed_config = config.get(
        "entity_name_description_embed", base_text_embed
    )
    skip_name_embedding = config.get("skip_name_embedding", False)
    skip_description_embedding = config.get("skip_description_embedding", False)
    is_using_vector_store = (
        entity_name_embed_config.get("strategy", {}).get("vector_store", None)
        is not None
    )

    def get_graph_column(df) -> Optional[str]:
        """Determine the correct graph column name."""
        possible_names = ["clustered_graph", "graph", "entity_graph"]
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    return [
        {
            "verb": "custom",
            "args": {
                "func": lambda df: df.assign(graph_column=get_graph_column(df))
            }
        },
        {
            "verb": "filter",
            "args": {
                "column": "graph_column",
                "criteria": [
                    {
                        "type": "value",
                        "operator": "is not empty",
                    }
                ],
            },
        },
        {
            "verb": "unpack_graph",
            "args": {
                "column": lambda df: df["graph_column"].iloc[0],
                "type": "nodes",
            },
            "input": {"source": "workflow:create_base_entity_graph"},
        },
        {"verb": "rename", "args": {"columns": {"label": "title"}}},
        {
            "verb": "select",
            "args": {
                "columns": [
                    "id",
                    "title",
                    "type",
                    "description",
                    "human_readable_id",
                    "graph_embedding",
                    "source_id",
                ],
            },
        },
        {
            "verb": "dedupe",
            "args": {"columns": ["id"]},
        },
        {"verb": "rename", "args": {"columns": {"title": "name"}}},
        {
            "verb": "filter",
            "args": {
                "column": "name",
                "criteria": [
                    {
                        "type": "value",
                        "operator": "is not empty",
                    }
                ],
            },
        },
        {
            "verb": "text_split",
            "args": {"separator": ",", "column": "source_id", "to": "text_unit_ids"},
        },
        {"verb": "drop", "args": {"columns": ["source_id"]}},
        {
            "verb": "text_embed",
            "enabled": not skip_name_embedding,
            "args": {
                "embedding_name": "entity_name",
                "column": "name",
                "to": "name_embedding",
                **entity_name_embed_config,
            },
        },
        {
            "verb": "merge",
            "enabled": not skip_description_embedding,
            "args": {
                "strategy": "concat",
                "columns": ["name", "description"],
                "to": "name_description",
                "delimiter": ":",
                "preserveSource": True,
            },
        },
        {
            "verb": "text_embed",
            "enabled": not skip_description_embedding,
            "args": {
                "embedding_name": "entity_name_description",
                "column": "name_description",
                "to": "description_embedding",
                **entity_name_description_embed_config,
            },
        },
        {
            "verb": "drop",
            "enabled": not skip_description_embedding,
            "args": {
                "columns": ["name_description"],
            },
        },
        {
            "verb": "filter",
            "enabled": not skip_description_embedding and not is_using_vector_store,
            "args": {
                "column": "description_embedding",
                "criteria": [
                    {
                        "type": "value",
                        "operator": "is not empty",
                    }
                ],
            },
        },
    ]
