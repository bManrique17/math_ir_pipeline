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
          <li className="nav-item">
            <NavLink to="/vocab" className={tabClass}>
              Vocab
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/retrieval" className={tabClass}>
              Formula retrieval
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/multimodal_retrieval" className={tabClass}>
              Multimodal retrieval
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/annotated_retrieval" className={tabClass}>
              Annotated formula retrieval
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/multimodal_retrieval_annotated" className={tabClass}>
              Annotated multimodal retrieval
            </NavLink>
          </li>
          <li className="nav-item">
            <NavLink to="/task1" className={tabClass}>
              ARQMath Task 1
            </NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}
