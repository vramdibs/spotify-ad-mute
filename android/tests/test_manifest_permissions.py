import xml.etree.ElementTree as tree
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = {"a": "http://schemas.android.com/apk/res/android"}


def test_only_modify_audio_settings():
    document = tree.parse(ROOT / "app/src/main/AndroidManifest.xml")
    names = []
    for node in document.getroot().findall("uses-permission"):
        names.append(node.attrib["{http://schemas.android.com/apk/res/android}name"])
    assert names == ["android.permission.MODIFY_AUDIO_SETTINGS"]


def test_queries_only_spotify():
    document = tree.parse(ROOT / "app/src/main/AndroidManifest.xml")
    packages = []
    for node in document.getroot().findall("queries/package"):
        packages.append(node.attrib["{http://schemas.android.com/apk/res/android}name"])
    assert packages == ["com.spotify.music"]


def test_service_is_spotify_only_and_debounced():
    xml = tree.parse(ROOT / "app/src/main/res/xml/spotify_ad_service.xml")
    node = xml.getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    assert node.attrib[android + "packageNames"] == "com.spotify.music"
    assert node.attrib[android + "notificationTimeout"] == "500"
    assert "typeWindowContentChanged" in node.attrib[android + "accessibilityEventTypes"]
