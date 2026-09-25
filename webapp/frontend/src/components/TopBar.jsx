import { NavLink } from "react-router-dom";

const tabClass = ({ isActive }) => `nav-link ${isActive ? "active" : ""}`;

export default function TopBar() {
  return (
    <nav className="navbar navbar-expand bg-body-tertiary border-bottom">
      <div className="container">
        <span className="navbar-brand mb-0">Cool stuff</span>
        <ul className="nav nav-tabs border-0">
          <li className="nav-item">
            <NavLink to="/" end className={tabClass}>
              Posts
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/formulas" className={tabClass}>
              Formulas
            </NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}
