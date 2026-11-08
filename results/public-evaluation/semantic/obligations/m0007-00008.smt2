(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 2))
(declare-fun s_6 () (_ BitVec 2))
(assert
 (let ((?x2810 (ite (= (_ bv3 2) s_7) (_ bv1 1) (_ bv0 1))))
 (let ((?x906 (ite (= (_ bv3 2) s_6) (_ bv1 1) (_ bv0 1))))
 (let ((?x92 (bvand ?x906 ?x2810)))
 (not (= ?x92 (_ bv1 1)))))))
(assert
 (let ((?x906 (ite (= (_ bv3 2) s_6) (_ bv1 1) (_ bv0 1))))
(let ((?x2810 (ite (= (_ bv3 2) s_7) (_ bv1 1) (_ bv0 1))))
(let ((?x92 (bvand ?x906 ?x2810)))
(let (($x31 (and (distinct ?x92 ?x906) true)))
(not $x31))))))
(check-sat)
