import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_image(client: AsyncClient):
    files = {'file': ('test.jpg', b'test content', 'image/jpeg')}
    response = await client.post("/images/", files=files, data={"tags": ["nature", "test"], "description": "A test image"})
    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".jpg")
    assert "download_url" in data
    assert "nature" in data["tags"]
    return data["id"]

@pytest.mark.asyncio
async def test_list_images(client: AsyncClient):
    # First upload an image to ensure there is something
    files = {'file': ('list_test.png', b'png content', 'image/png')}
    await client.post("/images/", files=files, data={"tags": ["list_tag"], "description": "List test"})
    
    # List with tag filter
    response = await client.get("/images/?tag=list_tag")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "list_tag" in data[0]["tags"]

@pytest.mark.asyncio
async def test_get_image(client: AsyncClient):
    # Upload
    files = {'file': ('get_test.txt', b'text data', 'text/plain')}
    upload_res = await client.post("/images/", files=files)
    image_id = upload_res.json()["id"]

    # Get
    response = await client.get(f"/images/{image_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == image_id
    assert data["download_url"] is not None

@pytest.mark.asyncio
async def test_delete_image(client: AsyncClient):
    # Upload
    files = {'file': ('del_test.jpg', b'del', 'image/jpeg')}
    upload_res = await client.post("/images/", files=files)
    image_id = upload_res.json()["id"]

    # Delete
    response = await client.delete(f"/images/{image_id}")
    assert response.status_code == 200
    
    # Verify Get fails
    get_res = await client.get(f"/images/{image_id}")
    assert get_res.status_code == 404
