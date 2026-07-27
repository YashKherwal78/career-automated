import hashlib

class SchemaDetector:
    @staticmethod
    def extract_structure(payload: dict | list | str | int | float | bool | None, prefix: str = "") -> list:
        """
        Recursively extracts the structural type signature of a JSON payload.
        Example: {"jobs": [{"title": "Eng"}]} -> ["jobs:list[object]", "jobs[].title:str"]
        """
        signature = []
        
        if isinstance(payload, dict):
            for k, v in sorted(payload.items()):
                new_prefix = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    signature.append(f"{new_prefix}:object")
                    signature.extend(SchemaDetector.extract_structure(v, new_prefix))
                elif isinstance(v, list):
                    signature.append(f"{new_prefix}:list")
                    if len(v) > 0:
                        # Map the first element to represent the list type
                        first_elem = v[0]
                        if isinstance(first_elem, dict):
                            signature.append(f"{new_prefix}[]:object")
                            signature.extend(SchemaDetector.extract_structure(first_elem, f"{new_prefix}[]"))
                        else:
                            signature.append(f"{new_prefix}[]:{type(first_elem).__name__}")
                else:
                    type_str = type(v).__name__ if v is not None else "null"
                    signature.append(f"{new_prefix}:{type_str}")
                    
        elif isinstance(payload, list):
            if len(payload) > 0:
                first_elem = payload[0]
                if isinstance(first_elem, dict):
                    signature.append(f"{prefix}[]:object")
                    signature.extend(SchemaDetector.extract_structure(first_elem, f"{prefix}[]"))
                else:
                    signature.append(f"{prefix}[]:{type(first_elem).__name__}")
        else:
            type_str = type(payload).__name__ if payload is not None else "null"
            signature.append(f"{prefix}:{type_str}")
            
        return signature

    @staticmethod
    def compute_schema_hash(payload: dict | bytes) -> str:
        """
        Computes a deterministic hash of the structural signature.
        If payload is raw bytes (like HTML), we just hash the bytes directly for now.
        """
        import json
        
        if isinstance(payload, bytes):
            # For raw non-JSON payloads (like raw HTML), structural hashing is harder.
            # We fallback to hashing the content or a simplified subset if possible.
            # For now, just hash the bytes (though this will trigger schemas often for HTML).
            return hashlib.sha256(payload).hexdigest()
            
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return hashlib.sha256(payload.encode('utf-8')).hexdigest()

        structure = SchemaDetector.extract_structure(payload)
        structure_str = ",".join(sorted(structure))
        return hashlib.sha256(structure_str.encode('utf-8')).hexdigest()
