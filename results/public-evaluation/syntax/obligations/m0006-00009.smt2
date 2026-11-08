(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 (not (= (ite (= (_ bv15 4) s_4) (_ bv1 1) (_ bv0 1)) (_ bv1 1))))
(assert
 (let (($x1303 (bvsge s_4 (_ bv14 4))))
(not $x1303)))
(check-sat)
