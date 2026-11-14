import { FiCheckCircle } from 'react-icons/fi'
import {
  FaBath, FaBed, FaBell, FaCar, FaCoffee, FaDumbbell, FaFire, FaFireExtinguisher, FaFirstAid,
  FaHotTub, FaKey, FaLaptop, FaParking, FaPaw, FaShower, FaSmokingBan, FaSnowflake,
  FaSwimmingPool, FaTree, FaTv, FaUtensils, FaWifi, FaWind,
} from 'react-icons/fa'

// Amenity.icon (react-icons naam) ka chhota curated map. Unknown icon => tick.
const ICONS = {
  FaBath, FaBed, FaBell, FaCar, FaCoffee, FaDumbbell, FaFire, FaFireExtinguisher, FaFirstAid,
  FaHotTub, FaKey, FaLaptop, FaParking, FaPaw, FaShower, FaSmokingBan, FaSnowflake,
  FaSwimmingPool, FaTree, FaTv, FaUtensils, FaWifi, FaWind,
}

export default function AmenityIcon({ name, className = 'h-5 w-5' }) {
  const Icon = ICONS[name] ?? FiCheckCircle
  return <Icon className={className} />
}