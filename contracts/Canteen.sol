    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    /**
     * @title Canteen
     * @dev Container orchestration with FHE encrypted memory management
     */
    contract Canteen {
        struct Member {
            string imageName;
            bytes encryptedMemory;  // FHE encrypted memory value
            bool active;
        }

        struct Image {
            uint replicas;
            uint deployed;
            bool active;
        }

        address public owner;

        event MemberJoin(string host, bytes encryptedMemory);
        event MemberLeave(string host);
        event MemberImageUpdate(string host, string image);
        event MemberMemoryUpdate(string host, bytes newEncryptedMemory);

        mapping(bytes32 => Member) memberDetails;
        string[] public members;

        mapping(bytes32 => Image) imageDetails;
        string[] public images;
        mapping (bytes32 => uint[2][]) exposedPortsForImages;

        uint MULT = 100000;

        modifier restricted() {
            require(msg.sender == owner, "Only owner can call this");
            _;
        }

        constructor() {
            owner = msg.sender;
        }

        /**
         * @dev Register a new member with encrypted memory
         * @param host The host identifier (peer ID)
         * @param encryptedMemory The FHE encrypted memory value (pass empty bytes for backward compatibility)
         */
        function addMember(string memory host, bytes memory encryptedMemory) restricted public {
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            require(!memberDetails[hashedHost].active);

            members.push(host);
            memberDetails[hashedHost] = Member("", encryptedMemory, true);

            emit MemberJoin(host, encryptedMemory);
            setImageForMember(host);
        }

        /**
         * @dev Backward compatible addMember without encrypted memory
         */
        function addMember(string memory host) restricted public {
            addMember(host, "");
        }

        /**
         * @dev Update member's encrypted memory after deployment
         * @param host The host identifier
         * @param newEncryptedMemory The new FHE encrypted memory value
         */
        function updateMemberMemory(string memory host, bytes memory newEncryptedMemory) restricted public {
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            require(memberDetails[hashedHost].active, "Member not active");

            memberDetails[hashedHost].encryptedMemory = newEncryptedMemory;
            emit MemberMemoryUpdate(host, newEncryptedMemory);
        }

        /**
         * @dev Get member's encrypted memory
         */
        function getMemberEncryptedMemory(string memory host) public view returns (bytes memory) {
            return memberDetails[keccak256(abi.encodePacked(host))].encryptedMemory;
        }

        function removeMember(string memory host) restricted public {
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            require(memberDetails[hashedHost].active);

            string memory affectedImage = memberDetails[hashedHost].imageName;

            if (keccak256(abi.encodePacked(affectedImage)) != keccak256(abi.encodePacked(""))) {
                imageDetails[keccak256(abi.encodePacked(affectedImage))].deployed -= 1;
                
                // Need to rebalance
                // Eg. (A, 4), (B, 4) are two images. We have 4 members, and we remove 2
                // We now have A A null null -> We would need A B null null
                rebalanceWithUnfortunateImage(affectedImage);
            }
            
            memberDetails[hashedHost] = Member("", "", false);

            emit MemberLeave(host);
        }

        function addImage(string memory name, uint replicas) restricted public {
            bytes32 hashedName = keccak256(abi.encodePacked(name));
            require(!imageDetails[hashedName].active);
            require(bytes(name).length > 0);
            require(replicas > 0);

            images.push(name);
            imageDetails[hashedName] = Image(replicas, 0, true);

            // Need to rebalance
            // Eg. (A, 4) is one image. We have 4 members. Now we add (B, 4)
            // We now have A A A A -> We would need A B A B
            rebalanceWithUnfortunateImage(name);
        }

        function removeImage(string memory name) restricted public {
            bytes32 hashedName = keccak256(abi.encodePacked(name));
            require(imageDetails[hashedName].active);

            imageDetails[hashedName].active = false;

            // Reassigns all the affected hosts to new images
            for (uint i = 0; i < members.length; i++) {
                Member storage member = memberDetails[keccak256(abi.encodePacked(members[i]))];
                if (member.active && keccak256(abi.encodePacked(member.imageName)) == hashedName) {
                    member.imageName = "";
                    setImageForMember(members[i]);
                }
            }
        }

        function addPortForImage(string memory name, uint from, uint to) restricted public {
            exposedPortsForImages[keccak256(abi.encodePacked(name))].push([from, to]);
        }

         function getPortsForImage(string memory name) restricted public view returns (uint[2][] memory) {
            return exposedPortsForImages[keccak256(abi.encodePacked(name))];
        }

        function getMemberDetails(string memory host) public view returns (string memory, bool, bytes memory) {
            Member storage details = memberDetails[keccak256(abi.encodePacked(host))];
            return (details.imageName, details.active, details.encryptedMemory);
        }

        function getImageDetails(string memory name) public view returns (uint, uint, bool) {
            Image storage details = imageDetails[keccak256(abi.encodePacked(name))];
            return (details.replicas, details.deployed, details.active);
        }

        function rebalanceWithUnfortunateImage(string memory newImageName) private {
            Image storage newImage = imageDetails[keccak256(abi.encodePacked(newImageName))];
            
            // Deploy replicas one by one, each time selecting node with highest memory
            while (newImage.deployed < newImage.replicas) {
                // Find node with highest memory that doesn't have an image
                string memory bestHost = findNodeWithHighestMemory("");
                
                if (keccak256(abi.encodePacked(bestHost)) == keccak256(abi.encodePacked(""))) {
                    // No available node found
                    break;
                }
                
                // Assign image to the node with highest memory
                bytes32 hashedBestHost = keccak256(abi.encodePacked(bestHost));
                memberDetails[hashedBestHost].imageName = newImageName;
                newImage.deployed += 1;
                emit MemberImageUpdate(bestHost, newImageName);
            }
        }

        function setImageForMember(string memory host) private {
            string memory image = getNextImageToUse();
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            bytes32 hashedImage = keccak256(abi.encodePacked(image));
            if (hashedImage == keccak256(abi.encodePacked(""))) {
                return;
            }

            // Host currently has no image, and image hasn't reached its limit yet.
            require(keccak256(abi.encodePacked(memberDetails[hashedHost].imageName)) == keccak256(abi.encodePacked("")));
            require(imageDetails[hashedImage].deployed < imageDetails[hashedImage].replicas);

            // Instead of assigning to the requesting host, find the node with highest memory
            string memory bestHost = findNodeWithHighestMemory(image);
            
            // If no suitable host found with FHE comparison, use the requesting host
            if (keccak256(abi.encodePacked(bestHost)) == keccak256(abi.encodePacked(""))) {
                bestHost = host;
            }
            
            bytes32 hashedBestHost = keccak256(abi.encodePacked(bestHost));
            memberDetails[hashedBestHost].imageName = image;
            imageDetails[hashedImage].deployed += 1;
            emit MemberImageUpdate(bestHost, image);
        }

        /**
         * @dev Find node with highest encrypted memory for image deployment.
         * Uses FHE comparison to select optimal node without decrypting memory values.
         * @return The host with highest encrypted memory
         */
        function findNodeWithHighestMemory(string memory) private view returns (string memory) {
            string memory bestHost = "";
            bytes memory highestMemory = "";
            
            // Iterate through all members to find the one with highest encrypted memory
            for (uint i = 0; i < members.length; i++) {
                bytes32 hashedMember = keccak256(abi.encodePacked(members[i]));
                Member storage member = memberDetails[hashedMember];
                
                // Skip if not active or already has an image assigned
                if (!member.active || keccak256(abi.encodePacked(member.imageName)) != keccak256(abi.encodePacked(""))) {
                    continue;
                }
                
                // Skip if no encrypted memory data
                if (member.encryptedMemory.length == 0) {
                    continue;
                }
                
                // First valid member becomes initial candidate
                if (highestMemory.length == 0) {
                    bestHost = members[i];
                    highestMemory = member.encryptedMemory;
                    continue;
                }
                
                // FHE Comparison: Compare encrypted memory values
                // In production, this would use actual FHE comparison operations
                // For now, we use a simple comparison as placeholder
                // TODO: Integrate with Zama fhEVM for on-chain FHE operations
                if (compareEncryptedMemory(member.encryptedMemory, highestMemory)) {
                    bestHost = members[i];
                    highestMemory = member.encryptedMemory;
                }
            }
            
            return bestHost;
        }

        /**
         * @dev Compare two encrypted memory values.
         * Returns true if memoryA > memoryB (encrypted comparison).
         * 
         * NOTE: This is a placeholder for actual FHE comparison.
         * In production with Zama fhEVM, this would perform homomorphic comparison
         * without ever decrypting the values.
         * 
         * @param memoryA First encrypted memory value
         * @param memoryB Second encrypted memory value
         * @return true if memoryA > memoryB
         */
        function compareEncryptedMemory(bytes memory memoryA, bytes memory memoryB) private pure returns (bool) {
            // Placeholder: In production, this would use Zama fhEVM's euint comparison
            // For now, we compare based on ciphertext size (longer = more precision = likely higher value)
            // This is NOT cryptographically correct but demonstrates the architecture
            
            // In real implementation with fhEVM:
            // euint32 valueA = TFHE.asEuint32(memoryA);
            // euint32 valueB = TFHE.asEuint32(memoryB);
            // return TFHE.decrypt(TFHE.gt(valueA, valueB));
            
            return memoryA.length >= memoryB.length;
        }

        // Selects image with lowest usage, scales equal usage of all replicas,
        // with respect to the ratio of the replicas required.
        function getNextImageToUse() private view returns (string memory) {
            string memory bestImage = "";
            uint lowestUsage = MULT;

            for (uint i = 0; i < images.length; i++) {
                bytes32 hash = keccak256(abi.encodePacked(images[i]));
                Image storage image = imageDetails[hash];

                if (image.deployed >= image.replicas)
                    continue;

                // deployed / usage < lowestUsage -> this has lower usage
                if (image.active && image.deployed < lowestUsage * image.replicas) {
                    lowestUsage = (image.deployed * MULT) / image.replicas;
                    bestImage = images[i];
                }
            }

            return bestImage;
        }

        function getMembersCount() public view returns (uint) {
            return members.length;
        }

        function getImagesCount() public view returns (uint) {
            return images.length;
        }
    }