from scripts.find_flash_attn_wheel import pick_best_wheel

# Real filenames pulled from mjun0812/flash-attention-prebuild-wheels'
# release history at design time - fixtures, not live network data.
ASSET_NAMES = [
    "flash_attn-2.5.9+cu124torch2.7-cp310-cp310-win_amd64.whl",
    "flash_attn-2.5.9+cu128torch2.7-cp310-cp310-win_amd64.whl",
    "flash_attn-2.6.3+cu128torch2.7-cp310-cp310-win_amd64.whl",
    "flash_attn-2.6.3+cu128torch2.7-cp312-cp312-win_amd64.whl",
    "flash_attn-2.7.4+cu128torch2.7-cp312-cp312-win_amd64.whl",
    "flash_attn-2.8.3+cu128torch2.7-cp310-cp310-win_amd64.whl",
    "flash_attn-2.8.3+cu128torch2.7-cp311-cp311-win_amd64.whl",
    "flash_attn-2.8.3+cu128torch2.7-cp312-cp312-win_amd64.whl",
    "flash_attn-2.8.3+cu128torch2.7-cp313-cp313-win_amd64.whl",
    "flash_attn-2.8.3+cu126torch2.7-cp312-cp312-win_amd64.whl",
    "flash_attn-2.8.3+cu128torch2.7-cp312-cp312-linux_x86_64.whl",
    "flash_attn-2.8.3+cu126torch2.13-cp312-cp312-win_amd64.whl",
    "flash_attn_3-3.0.0+cu126torch2.13gite2743ab-cp39-abi3-linux_aarch64.whl",
    "not-a-flash-attn-wheel.whl",
]


def test_picks_highest_version_for_exact_match():
    result = pick_best_wheel(ASSET_NAMES, py_tag="cp312", platform_tag_="win_amd64")
    assert result == "flash_attn-2.8.3+cu128torch2.7-cp312-cp312-win_amd64.whl"


def test_only_one_candidate_for_cp313():
    result = pick_best_wheel(ASSET_NAMES, py_tag="cp313", platform_tag_="win_amd64")
    assert result == "flash_attn-2.8.3+cu128torch2.7-cp313-cp313-win_amd64.whl"


def test_picks_linux_platform_over_windows():
    result = pick_best_wheel(ASSET_NAMES, py_tag="cp312", platform_tag_="linux_x86_64")
    assert result == "flash_attn-2.8.3+cu128torch2.7-cp312-cp312-linux_x86_64.whl"


def test_ignores_wrong_cuda_tag():
    # cu126 build for cp312/win_amd64 exists but must not be returned
    # when the default cu128 pin is requested.
    result = pick_best_wheel(ASSET_NAMES, py_tag="cp312", platform_tag_="win_amd64", cuda_tag="cu128")
    assert result is not None
    assert "cu126" not in result


def test_ignores_wrong_torch_tag():
    result = pick_best_wheel(
        ASSET_NAMES, py_tag="cp312", platform_tag_="win_amd64", torch_tag="torch2.13", cuda_tag="cu126"
    )
    assert result == "flash_attn-2.8.3+cu126torch2.13-cp312-cp312-win_amd64.whl"


def test_ignores_flash_attn_3_variant():
    result = pick_best_wheel(
        ["flash_attn_3-3.0.0+cu126torch2.13gite2743ab-cp39-abi3-linux_aarch64.whl"],
        py_tag="cp39",
        platform_tag_="linux_aarch64",
    )
    assert result is None


def test_no_match_returns_none():
    result = pick_best_wheel(ASSET_NAMES, py_tag="cp39", platform_tag_="win_amd64")
    assert result is None
