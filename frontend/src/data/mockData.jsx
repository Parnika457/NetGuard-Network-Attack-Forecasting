export const networkData = [
  {
    time: "12:30",
    packets: 420,
    throughput: 1.2,
    flows: 64,
    connections: 21,
    inbound: 0.7,
    outbound: 0.5,
    risk: 18,
  },
  {
    time: "12:31",
    packets: 510,
    throughput: 1.5,
    flows: 72,
    connections: 23,
    inbound: 0.9,
    outbound: 0.6,
    risk: 21,
  },
  {
    time: "12:32",
    packets: 470,
    throughput: 1.4,
    flows: 69,
    connections: 25,
    inbound: 0.8,
    outbound: 0.6,
    risk: 24,
  },
  {
    time: "12:33",
    packets: 620,
    throughput: 1.8,
    flows: 81,
    connections: 28,
    inbound: 1.1,
    outbound: 0.7,
    risk: 31,
  },
  {
    time: "12:34",
    packets: 710,
    throughput: 2.1,
    flows: 94,
    connections: 31,
    inbound: 1.3,
    outbound: 0.8,
    risk: 39,
  },
  {
    time: "12:35",
    packets: 850,
    throughput: 2.4,
    flows: 120,
    connections: 34,
    inbound: 1.5,
    outbound: 0.9,
    risk: 87,
  },
  {
    time: "12:36",
    packets: 790,
    throughput: 2.2,
    flows: 112,
    connections: 33,
    inbound: 1.4,
    outbound: 0.8,
    risk: 82,
  },
  {
    time: "12:37",
    packets: 730,
    throughput: 2.0,
    flows: 106,
    connections: 31,
    inbound: 1.2,
    outbound: 0.8,
    risk: 76,
  },
  {
    time: "12:38",
    packets: 680,
    throughput: 1.9,
    flows: 98,
    connections: 29,
    inbound: 1.1,
    outbound: 0.8,
    risk: 69,
  },
];

export const protocolData = [
  { name: "TCP", value: 68 },
  { name: "UDP", value: 24 },
  { name: "ICMP", value: 5 },
  { name: "Other", value: 3 },
];

export const currentForecast = {
  id: "F-20260927-001",

  attackType: "Port Scanning",

  category: "Network Reconnaissance",

  severity: "HIGH",

  confidence: 91,

  riskScore: 87,

  leadTimeSeconds: 342,

  evidence: [
    {
      label: "Connection rate",
      value: "+42%",
      score: 88,
    },
    {
      label: "Unique destination ports",
      value: "18",
      score: 81,
    },
    {
      label: "Repeated source activity",
      value: "7 events",
      score: 74,
    },
    {
      label: "Sequential behavior",
      value: "High",
      score: 91,
    },
  ],

  interpretation:
    "The model identified an increase in connection attempts across multiple destination ports combined with repeated source activity. This pattern increased the predicted probability of Port Scanning.",

  recommendations: [
    "Restrict suspicious source",
    "Increase monitoring",
    "Investigate targeted host",
  ],

  timestamp: "2026-09-27T12:41:00",
};

export const attackHistory = [
  {
    id: "A-001",
    attackType: "Port Scanning",
    category: "Network Reconnaissance",
    severity: "HIGH",
    confidence: 91,
    riskScore: 87,
    leadTime: "5–15 minutes",
    date: "27 Sep 2026",
    time: "12:41 PM",
    status: "FORECASTED",
    action: "Recommendation generated",
  },

  {
    id: "A-002",
    attackType: "Brute Force",
    category: "Credential Access",
    severity: "MEDIUM",
    confidence: 82,
    riskScore: 68,
    leadTime: "15–30 minutes",
    date: "27 Sep 2026",
    time: "10:22 AM",
    status: "RESOLVED",
    action: "Increased monitoring",
  },

  {
    id: "A-003",
    attackType: "DoS Attack",
    category: "Denial of Service",
    severity: "HIGH",
    confidence: 94,
    riskScore: 91,
    leadTime: "<5 minutes",
    date: "26 Sep 2026",
    time: "7:18 PM",
    status: "RESOLVED",
    action: "Source traffic flagged",
  },

  {
    id: "A-004",
    attackType: "Web Attack",
    category: "Web Application",
    severity: "MEDIUM",
    confidence: 79,
    riskScore: 62,
    leadTime: "15–30 minutes",
    date: "26 Sep 2026",
    time: "4:07 PM",
    status: "RESOLVED",
    action: "Investigation recommended",
  },
];

export const attackDictionary = [
  {
    type: "Port Scanning",
    category: "Network Reconnaissance",
    icon: "◎",

    description:
      "Attempts to discover accessible ports and services on a network host.",

    indicators: [
      "High connection frequency",
      "Multiple destination ports",
      "Repeated source activity",
    ],

    defenses: [
      "Restrict suspicious sources",
      "Monitor exposed services",
      "Review firewall rules",
    ],
  },

  {
    type: "Brute Force",
    category: "Credential Access",
    icon: "⌁",

    description:
      "Repeated authentication attempts intended to discover valid credentials.",

    indicators: [
      "Repeated login attempts",
      "Multiple credential combinations",
      "Abnormal authentication frequency",
    ],

    defenses: [
      "Rate-limit authentication",
      "Enable account lockout policies",
      "Increase authentication monitoring",
    ],
  },

  {
    type: "DoS / DDoS",
    category: "Denial of Service",
    icon: "◈",

    description:
      "Traffic patterns intended to overwhelm a service or network resource.",

    indicators: [
      "Rapid traffic increase",
      "Large packet volume",
      "Abnormal connection rate",
    ],

    defenses: [
      "Rate-limit traffic",
      "Filter suspicious sources",
      "Increase service monitoring",
    ],
  },

  {
    type: "Web Attack",
    category: "Web Application",
    icon: "◇",

    description:
      "Malicious activity targeting web applications and their interfaces.",

    indicators: [
      "Abnormal request patterns",
      "Suspicious payloads",
      "Repeated application errors",
    ],

    defenses: [
      "Inspect application requests",
      "Apply input validation",
      "Increase web monitoring",
    ],
  },
];