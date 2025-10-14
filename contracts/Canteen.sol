    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    contract Canteen {
        struct Member {
            string imageName;
            bool active;
        }

        struct Image {
            uint replicas;
            uint deployed;
            bool active;
        }

        address public owner;

        event MemberJoin(string host);
        event MemberLeave(string host);
        event MemberImageUpdate(string host, string image);

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

        function addMember(string memory host) restricted public {
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            require(!memberDetails[hashedHost].active);

            members.push(host);
            memberDetails[hashedHost] = Member("", true);

            emit MemberJoin(host);
            setImageForMember(host);
        }

        function removeMember(string memory host) restricted public {
            bytes32 hashedHost = keccak256(abi.encodePacked(host));
            require(memberDetails[hashedHost].active);

            string memory affectedImage = memberDetails[hashedHost].imageName;

            imageDetails[keccak256(abi.encodePacked(affectedImage))].deployed -= 1;
            memberDetails[hashedHost] = Member("", false);

            emit MemberLeave(host);

            // Need to rebalance
            // Eg. (A, 4), (B, 4) are two images. We have 4 members, and we remove 2
            // We now have A A null null -> We would need A B null null
            rebalanceWithUnfortunateImage(affectedImage);
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

        function getMemberDetails(string memory host) public view returns (string memory, bool) {
            Member storage details = memberDetails[keccak256(abi.encodePacked(host))];
            return (details.imageName, details.active);
        }

        function getImageDetails(string memory name) public view returns (uint, uint, bool) {
            Image storage details = imageDetails[keccak256(abi.encodePacked(name))];
            return (details.replicas, details.deployed, details.active);
        }

        function rebalanceWithUnfortunateImage(string memory newImageName) private {
            Image storage newImage = imageDetails[keccak256(abi.encodePacked(newImageName))];
            uint currentRatio = 0;
            uint i;
            Member storage member;

            for (i = 0; i < members.length; i++) {
                if (newImage.deployed >= newImage.replicas)
                    break;

                member = memberDetails[keccak256(abi.encodePacked(members[i]))];
                // Looking for empty hosts and filling them up
                if (member.active && keccak256(abi.encodePacked(member.imageName)) == keccak256(abi.encodePacked(""))) {
                    member.imageName = newImageName;
                    newImage.deployed += 1;
                    currentRatio += (MULT / newImage.replicas);
                    emit MemberImageUpdate(members[i], newImageName);
                }
            }

            for (i = 0; i < members.length; i++) {
                if (newImage.deployed >= newImage.replicas)
                    break;

                member = memberDetails[keccak256(abi.encodePacked(members[i]))];
                // Now we are processing those hosts which already have images on them
                if (member.active && keccak256(abi.encodePacked(member.imageName)) != keccak256(abi.encodePacked(""))) {
                    // Only check if the machine has some other host running
                    if (keccak256(abi.encodePacked(member.imageName)) != keccak256(abi.encodePacked(newImageName))) {
                        Image storage image = imageDetails[keccak256(abi.encodePacked(member.imageName))];
                        uint ratio = (image.deployed * MULT) / image.replicas;
                        // if (ratio < currentRatio + (MULT / newImage.replicas)) {
                        if (ratio > currentRatio) {
                            member.imageName = newImageName;
                            newImage.deployed += 1;
                            image.deployed -= 1;
                            currentRatio += (MULT / newImage.replicas);
                            emit MemberImageUpdate(members[i], newImageName);
                        }
                    }
                }
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

            memberDetails[hashedHost] = Member(image, true);
            imageDetails[hashedImage].deployed += 1;
            emit MemberImageUpdate(host, image);
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