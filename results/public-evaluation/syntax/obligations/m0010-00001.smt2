(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(declare-fun s_11 () (Array (_ BitVec 8) (_ BitVec 32)))
(assert
 (let ((?x1532 (ite (bvult (select s_11 i_6) ((_ zero_extend 24) (_ bv200 8))) (_ bv1 1) (_ bv0 1))))
 (let ((?x2234 (bvnot ?x1532)))
 (let ((?x617 (bvand (_ bv1 1) ?x2234)))
 (not (= ?x617 (_ bv1 1)))))))
(assert
 (let ((?x184 (select s_11 i_6)))
(let ((?x1089 ((_ extract 7 0) ?x184)))
(let (($x602 (bvule (_ bv200 8) ?x1089)))
(let (($x45 (or (not (= ((_ extract 31 8) ?x184) (_ bv0 24))) $x602)))
(let (($x1442 (not $x45)))
(let (($x30 (not $x1442)))
(not $x30))))))))
(check-sat)
