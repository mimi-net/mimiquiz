import json
import os
import uuid
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from flask import flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

from miminet_jwt import external_url_for
from miminet_model import Network, Simulate, db
from quiz.util.dto import get_organization

# def external_url_for(endpoint, filename=None, **kwargs):
#     base = os.environ.get("EXTERNAL_BASE_URL", "localhost").rstrip("/")
#
#     if endpoint == "static":
#         static_url = os.environ.get("STATIC_SERVER_URL", "/static").strip("/")
#         endpoint = static_url if static_url else "static"
#
#     endpoint = endpoint.strip("/")
#     if filename is not None:
#         filename = filename.strip("/")
#         endpoint = f"{endpoint}/{filename}" if endpoint else filename
#
#     path = endpoint.lstrip("/")
#     query_string = urlencode(kwargs) if kwargs else ""
#
#     full_url = urljoin(base + "/", path)
#     if query_string:
#         parsed = urlparse(full_url)
#         full_url = urlunparse(
#             (
#                 parsed.scheme,
#                 parsed.netloc,
#                 parsed.path,
#                 parsed.params,
#                 query_string,
#                 parsed.fragment,
#             )
#         )
#
#     return full_url


def quiz_url_for(endpoint, filename=None, **kwargs):
    base = os.environ.get("QUIZ_URL", "localhost").rstrip("/")

    if endpoint == "static":
        static_url = os.environ.get("STATIC_SERVER_URL", "/static").strip("/")
        endpoint = static_url if static_url else "static"

    endpoint = endpoint.strip("/")
    if filename is not None:
        filename = filename.strip("/")
        endpoint = f"{endpoint}/{filename}" if endpoint else filename

    path = endpoint.lstrip("/")
    query_string = urlencode(kwargs) if kwargs else ""

    full_url = urljoin(base + "/", path)
    if query_string:
        parsed = urlparse(full_url)
        full_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                parsed.fragment,
            )
        )

    return full_url


@jwt_required()
def create_network():
    user_id = get_jwt_identity()
    u = uuid.uuid4()

    n = Network(author_id=user_id, guid=str(u))
    db.session.add(n)
    db.session.flush()
    db.session.refresh(n)
    db.session.commit()

    return redirect(url_for("web_network", guid=n.guid))


def web_network_shared():
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне открыть?!")
        return redirect(url_for("home"))

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash("Нет такой сети")
        return redirect(url_for("home"))

    if not net.share_mode:
        flash("Сеть закрыта для общего доступа")
        return redirect(url_for("home"))

    jnet = json.loads(net.network)

    # Do we simulated this network already
    sim = (
        Simulate.query.filter(Simulate.network_id == net.id)
        .order_by(Simulate.id.desc())
        .first()
    )
    jnet["packets"] = "null"

    if sim:
        if sim.ready:
            jnet["packets"] = sim.packets

    if "nodes" not in jnet:
        jnet["nodes"] = []

    if "edges" not in jnet:
        jnet["edges"] = []

    if "jobs" not in jnet:
        jnet["jobs"] = []

    if "config" not in jnet:
        jnet["config"] = {"zoom": 2, "pan_x": 0, "pan_y": 0}

    # Check if we have a pcaps. If not, try to check for it.
    if "pcap" not in jnet:
        jnet["pcap"] = []

    pcap_dir = "static/pcaps/" + network_guid

    if os.path.exists(pcap_dir):
        jnet["pcap"] = [
            os.path.splitext(f)[0]
            for f in os.listdir(pcap_dir)
            if os.path.isfile(os.path.join(pcap_dir, f))
        ]
        net.network = json.dumps(jnet)
        db.session.commit()

    json_nodes = json.dumps(jnet["nodes"])
    org = get_organization()

    return render_template(
        "network_shared.html",
        network=net,
        nodes=json_nodes,
        edges=jnet["edges"],
        packets=jnet["packets"],
        jobs=jnet["jobs"],
        network_config=jnet["config"],
        pcaps=jnet["pcap"],
        mimishark_nav=1,
        organization_logo_uri=org.logo_uri,
        organization_name=org.name,
    )


def web_network():
    network_guid = request.args.get("guid", type=str)

    if not network_guid:
        flash("Пропущен параметр GUID. И какую сеть мне открыть?!")
        return redirect(url_for("home"))

    net = Network.query.filter(Network.guid == network_guid).first()

    if not net:
        flash("Нет такой сети")
        return redirect("home")

    # Anonymous? Redirect to share version.
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        print(
            f"User ID: {user_id}; Net author: {net.author_id}; {user_id == net.author_id}"
        )
    except Exception:
        if net.share_mode:
            return redirect(
                external_url_for(
                    "auth",
                    filename="login.html",
                    next=(quiz_url_for("web_network", guid=net.guid)),
                )
            )
        else:
            return redirect(
                external_url_for(
                    "auth",
                    filename="login.html",
                    next=(quiz_url_for("web_network", guid=net.guid)),
                )
            )

    # If author is not user
    if str(net.author_id) != user_id:
        if net.share_mode:
            return redirect(
                external_url_for(
                    "auth",
                    filename="login.html",
                    next=(quiz_url_for("web_network", guid=net.guid)),
                )
            )
        else:
            return redirect(url_for("home"))

    jnet = json.loads(net.network)

    # Do we simulated this network already
    sim = (
        Simulate.query.filter(Simulate.network_id == net.id)
        .order_by(Simulate.id.desc())
        .first()
    )
    jnet["packets"] = "null"

    if sim:
        if sim.ready:
            jnet["packets"] = sim.packets

    if "nodes" not in jnet:
        jnet["nodes"] = []

    if "edges" not in jnet:
        jnet["edges"] = []

    if "jobs" not in jnet:
        jnet["jobs"] = []

    if "config" not in jnet:
        jnet["config"] = {"zoom": 2, "pan_x": 0, "pan_y": 0}

    # Check if we have a pcaps. If not, try to check for it.
    if "pcap" not in jnet:
        jnet["pcap"] = []

    pcap_dir = "static/pcaps/" + network_guid

    if os.path.exists(pcap_dir):
        jnet["pcap"] = [
            os.path.splitext(f)[0]
            for f in os.listdir(pcap_dir)
            if os.path.isfile(os.path.join(pcap_dir, f))
        ]
        net.network = json.dumps(jnet)
        db.session.commit()

    json_nodes = json.dumps(jnet["nodes"])
    org = get_organization()

    return render_template(
        "network.html",
        network=net,
        nodes=json_nodes,
        edges=jnet["edges"],
        packets=jnet["packets"],
        jobs=jnet["jobs"],
        simulating=sim,
        network_config=jnet["config"],
        pcaps=jnet["pcap"],
        mimishark_nav=1,
        organization_logo_uri=org.logo_uri,
        organization_name=org.name,
    )


def generate_image_uri(extension=".png"):
    return os.urandom(16).hex() + extension
