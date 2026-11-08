(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(declare-fun s_4 () (_ BitVec 4))
(assert
 (not (= (bvand (ite (bvugt s_4 (_ bv3 4)) (_ bv1 1) (_ bv0 1)) ((_ extract 0 0) s_3)) (_ bv1 1))))
(assert
 (let ((?x930 ((_ extract 0 0) s_3)))
(let (($x401 (and (distinct ?x930 (_ bv0 1)) true)))
(not $x401))))
(check-sat)
