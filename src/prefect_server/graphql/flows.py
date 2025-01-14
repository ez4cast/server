from typing import Any

from graphql import GraphQLResolveInfo

from prefect import api, models
from prefect.utilities.graphql import EnumValue, decompress
from prefect_server.utilities.graphql import mutation


@mutation.field("create_flow_from_compressed_string")
async def resolve_create_flow_from_compressed_string(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    try:
        serialized_flow = decompress(input["serialized_flow"])
    except:
        raise TypeError("Unable to decompress serialized flow")
    input["serialized_flow"] = serialized_flow
    return await resolve_create_flow(obj, info, input)


@mutation.field("create_flow")
async def resolve_create_flow(obj: Any, info: GraphQLResolveInfo, input: dict) -> dict:
    serialized_flow = input["serialized_flow"]
    project_id = input["project_id"]
    version_group_id = input.get("version_group_id", None)
    set_schedule_active = input.get("set_schedule_active", True)
    description = input.get("description", None)
    idempotency_key = input.get("idempotency_key", None)

    if project_id is None:
        raise ValueError("Invalid project ID")

    # if no version_group_id is supplied, see if a flow with the same name exists in this
    # project
    new_version_group = True
    if not version_group_id:
        flow = await models.Flow.where(
            {
                "project_id": {"_eq": project_id},
                "name": {"_eq": serialized_flow.get("name")},
            }
        ).first(
            order_by={"created": EnumValue("desc")}, selection_set={"version_group_id"}
        )
        if flow:
            version_group_id = flow.version_group_id  # type:ignore
            new_version_group = False
    # otherwise look the flow up directly using the version group ID
    else:
        flow = await models.Flow.where(
            {"version_group_id": {"_eq": version_group_id}}
        ).first(selection_set={"version_group_id"})
        if flow:
            new_version_group = False

    flow_id = await api.flows.create_flow(
        project_id=project_id,
        serialized_flow=serialized_flow,
        version_group_id=version_group_id,
        set_schedule_active=set_schedule_active,
        description=description,
        idempotency_key=idempotency_key,
    )

    # archive all other versions
    if version_group_id:
        all_other_unarchived_versions = await models.Flow.where(
            {
                "version_group_id": {"_eq": version_group_id},
                "id": {"_neq": flow_id},
                "archived": {"_eq": False},
            }
        ).get(
            {"id"}
        )  # type: Any

        for version in all_other_unarchived_versions:
            await api.flows.archive_flow(version.id)  # type: ignore

    return {"id": flow_id}


@mutation.field("register_tasks")
async def resolve_register_tasks(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    serialized_tasks = input["serialized_tasks"]
    flow_id = input["flow_id"]

    if flow_id is None:
        raise ValueError("Invalid flow ID")

    await api.flows.register_tasks(
        flow_id=flow_id, tenant_id=None, tasks=serialized_tasks
    )
    return {"success": True}


@mutation.field("register_edges")
async def resolve_register_edges(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    serialized_edges = input["serialized_edges"]
    flow_id = input["flow_id"]

    if flow_id is None:
        raise ValueError("Invalid flow ID")

    await api.flows.register_edges(
        flow_id=flow_id, tenant_id=None, edges=serialized_edges
    )
    return {"success": True}


@mutation.field("delete_flow")
async def resolve_delete_flow(obj: Any, info: GraphQLResolveInfo, input: dict) -> dict:
    return {"success": await api.flows.delete_flow(flow_id=input["flow_id"])}


@mutation.field("archive_flow")
async def resolve_archive_flow(obj: Any, info: GraphQLResolveInfo, input: dict) -> dict:
    return {"success": await api.flows.archive_flow(flow_id=input["flow_id"])}


@mutation.field("update_flow_project")
async def resolve_update_flow_project(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    return {
        "id": await api.flows.update_flow_project(
            flow_id=input["flow_id"], project_id=input["project_id"]
        )
    }


@mutation.field("disable_flow_heartbeat")
async def resolve_disable_heartbeat_for_flow(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    if not input["flow_id"]:
        raise ValueError("Invalid flow ID.")
    flow = await models.Flow.where(id=input["flow_id"]).first({"flow_group_id"})
    if not flow:
        raise ValueError("Invalid flow ID.")
    success = await api.flow_groups.disable_heartbeat(flow_group_id=flow.flow_group_id)
    return {"success": success}


@mutation.field("enable_flow_heartbeat")
async def resolve_enable_heartbeat_for_flow(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    if not input["flow_id"]:
        raise ValueError("Invalid flow ID.")
    flow = await models.Flow.where(id=input["flow_id"]).first({"flow_group_id"})
    if not flow:
        raise ValueError("Invalid flow ID.")
    success = await api.flow_groups.enable_heartbeat(flow_group_id=flow.flow_group_id)
    return {"success": success}


@mutation.field("enable_flow_lazarus_process")
async def resolve_enable_flow_lazarus_process(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    if not input["flow_id"]:
        raise ValueError("Invalid flow ID.")
    flow = await models.Flow.where(id=input["flow_id"]).first({"flow_group_id"})
    if not flow:
        raise ValueError("Invalid flow ID.")
    return {
        "success": await api.flow_groups.enable_lazarus(
            flow_group_id=flow.flow_group_id
        )
    }


@mutation.field("disable_flow_lazarus_process")
async def resolve_disable_flow_lazarus_process(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    if not input["flow_id"]:
        raise ValueError("Invalid flow ID.")
    flow = await models.Flow.where(id=input["flow_id"]).first({"flow_group_id"})
    if not flow:
        raise ValueError("Invalid flow ID.")
    return {
        "success": await api.flow_groups.disable_lazarus(
            flow_group_id=flow.flow_group_id
        )
    }


@mutation.field("set_schedule_active")
async def resolve_set_schedule_active(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    return {"success": await api.flows.set_schedule_active(flow_id=input["flow_id"])}


@mutation.field("set_schedule_inactive")
async def resolve_set_schedule_inactive(
    obj: Any, info: GraphQLResolveInfo, input: dict
) -> dict:
    return {"success": await api.flows.set_schedule_inactive(flow_id=input["flow_id"])}
