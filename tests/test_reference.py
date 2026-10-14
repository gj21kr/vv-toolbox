import numpy as np
import pytest
import base64
import zlib
from vv_toolbox.reference import contour_area,xml_document,read_vtp


def test_contour_area_is_rotation_and_translation_invariant():
    polygon=np.array([[0,0,0],[3,0,0],[3,4,0],[0,4,0]],float)
    rotation=np.array([[1,0,0],[0,.6,-.8],[0,.8,.6]])
    assert contour_area(polygon@rotation.T+100)==pytest.approx(12)


def test_legacy_xml_preserves_both_roots():
    root=xml_document(b'<?xml version="1.0"?><format version="1.0"/><path id="3"/>')
    assert root.find('path').get('id')=='3'


def test_zero_area_contour_rejected():
    with pytest.raises(ValueError):
        contour_area([[0,0,0],[1,0,0],[2,0,0]])


def test_compressed_vtp_decodes_original_triangles_and_converts_cm_to_mm():
    chunks=[]; offsets=[]; offset=0
    for values in [np.array([[0,0,0],[1,0,0],[0,1,0]],dtype='<f4'),np.array([0,1,2],dtype='<i8'),np.array([3],dtype='<i8')]:
        raw=values.tobytes();compressed=zlib.compress(raw)
        encoded=base64.b64encode(np.array([1,32768,len(raw),len(compressed)],dtype='<u4').tobytes()).decode()+base64.b64encode(compressed).decode()
        offsets.append(offset);chunks.append(encoded);offset+=len(encoded)
    data=f'''<VTKFile byte_order="LittleEndian" header_type="UInt32" compressor="vtkZLibDataCompressor"><PolyData><Piece><Points><DataArray type="Float32" offset="{offsets[0]}"/></Points><Polys><DataArray Name="connectivity" type="Int64" offset="{offsets[1]}"/><DataArray Name="offsets" type="Int64" offset="{offsets[2]}"/></Polys></Piece></PolyData><AppendedData encoding="base64">_{''.join(chunks)}</AppendedData></VTKFile>'''
    vertices,faces=read_vtp(data.encode())
    np.testing.assert_array_equal(vertices,[[0,0,0],[10,0,0],[0,10,0]])
    np.testing.assert_array_equal(faces,[[0,1,2]])
