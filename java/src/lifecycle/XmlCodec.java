package lifecycle;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.stream.XMLOutputFactory;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.xml.sax.SAXException;
import org.xml.sax.helpers.DefaultHandler;

/** Finite two-level XML envelope. No DTD, entities, arbitrary tree or extensible RPC. */
final class XmlCodec {
    record Envelope(String id, Map<String, String> fields) {}

    static Envelope read(byte[] bytes, String rootName, boolean protocol) throws Exception {
        var factory = DocumentBuilderFactory.newDefaultInstance();
        factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        factory.setAttribute("jdk.xml.maxElementDepth", "2");
        factory.setXIncludeAware(false);
        factory.setExpandEntityReferences(false);
        var builder = factory.newDocumentBuilder();
        builder.setEntityResolver((publicId, systemId) -> { throw new SAXException("External entity denied"); });
        builder.setErrorHandler(new DefaultHandler() {
            @Override public void error(org.xml.sax.SAXParseException e) throws SAXException { throw e; }
            @Override public void fatalError(org.xml.sax.SAXParseException e) throws SAXException { throw e; }
        });
        var doc = builder.parse(new ByteArrayInputStream(bytes));
        var root = doc.getDocumentElement();
        String versionKey = protocol ? "protocol" : "schema";
        if (!root.getTagName().equals(rootName) || !root.getAttribute(versionKey).equals("1")
                || root.getAttributes().getLength() != (protocol ? 2 : 1)) {
            throw new IllegalArgumentException("Invalid envelope/version");
        }
        String id = protocol ? root.getAttribute("id") : "";
        if (protocol && !id.matches("[0-9]{1,12}")) throw new IllegalArgumentException("Invalid request ID");
        Map<String, String> fields = new LinkedHashMap<>();
        for (Node node = root.getFirstChild(); node != null; node = node.getNextSibling()) {
            if (node.getNodeType() == Node.TEXT_NODE && node.getTextContent().isBlank()) continue;
            if (!(node instanceof Element field) || !field.getTagName().equals("field")
                    || field.getAttributes().getLength() != 1 || !field.hasAttribute("name")) {
                throw new IllegalArgumentException("Invalid field node");
            }
            String key = field.getAttribute("name");
            if (!key.matches("[a-z][a-z0-9_.]{0,63}")) throw new IllegalArgumentException("Invalid field key");
            for (Node child = field.getFirstChild(); child != null; child = child.getNextSibling()) {
                if (child.getNodeType() != Node.TEXT_NODE) throw new IllegalArgumentException("Nested XML denied");
            }
            String value = field.getTextContent();
            if (value.length() > 16_384 || fields.putIfAbsent(key, value) != null
                    || fields.size() > (protocol ? 20 : 512)) {
                throw new IllegalArgumentException("Duplicate or oversized fields");
            }
        }
        return new Envelope(id, fields);
    }

    static byte[] write(String root, String id, Map<String, String> fields) throws Exception {
        var bytes = new ByteArrayOutputStream();
        var writer = XMLOutputFactory.newDefaultFactory().createXMLStreamWriter(bytes, "UTF-8");
        writer.writeStartElement(root);
        writer.writeAttribute(root.equals("snapshot") ? "schema" : "protocol", "1");
        if (!root.equals("snapshot")) writer.writeAttribute("id", id);
        for (var entry : new java.util.TreeMap<>(fields).entrySet()) {
            writer.writeStartElement("field");
            writer.writeAttribute("name", entry.getKey());
            writer.writeCharacters(entry.getValue());
            writer.writeEndElement();
        }
        writer.writeEndElement();
        writer.close();
        return bytes.toByteArray();
    }
}
