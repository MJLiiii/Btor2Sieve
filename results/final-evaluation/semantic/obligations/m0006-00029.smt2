(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(declare-fun s_4 () (_ BitVec 4))
(assert
 (not (= (bvand (ite (bvugt s_4 (_ bv3 4)) (_ bv1 1) (_ bv0 1)) ((_ extract 0 0) s_3)) (_ bv1 1))))
(assert
 (let (($x649 (= ((_ extract 3 2) s_4) (_ bv0 2))))
(let (($x25 (not $x649)))
(let (($x1772 (not $x25)))
(not $x1772)))))
(check-sat)
